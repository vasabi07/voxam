from unstructured.partition.pdf import partition_pdf
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from enum import Enum
load_dotenv()


"""
1.get the query
2. use unstructured.partition.pdf to extract content from the PDF
3. split text, images and tables
4. for each chunk create questions (must create a class to use structured output) and put all questions in a list
5. for each list item, create cyphers in neo4j graphdb 
6. for the actual chunk create a summary and have embeddings put that in the db as well
connections should be like user-> document-> topics -> chunks(embeddings) -> questions 

"""
class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand" 
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"

class Difficulty(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class QuestionType(str, Enum):
    LONG_ANSWER = "long_answer"
    MULTIPLE_CHOICE = "multiple_choice"

class Question(BaseModel):
    text: str = Field(description= "the question text")
    bloom_level: BloomLevel = Field(description= "the bloom's taxonomy level")
    difficulty: Difficulty = Field(description= "the question difficulty level")
    question_type: QuestionType = Field(description= "the question type")
    expected_time: int  = Field(description= "the expected time to answer the question")
    key_points: List[str] = Field(description= "the key points to consider when answering the question")
    options: Optional[List[str]] = Field(description= "the options for the question")
    correct_answer: Optional[str] = Field(description= "the correct answer for the question")
    explanation: Optional[str] = Field(description= "the explanation for the correct answer")

class QuestionSet(BaseModel):
    """Container for all questions generated from a content block"""
    long_answer_questions: List[Question] = Field(description="Long answer questions")
    multiple_choice_questions: List[Question] = Field(description="Multiple choice questions") 
    total_questions: int = Field(description="Total number of questions")

class ContentBlock:
    def __init__(self):
        self.chunk_index: int = 0
        self.text_content: str = ""
        self.related_tables: List[str] = []
        self.image_captions: List[str] = []
        self.table_descriptions: List[str] = []
        self.combined_context: str = ""
        self.questions: List[Question] = []
        self.embeddings: List[float] = []
        self.summary: str = ""

class IngestionPipeline:
    def __init__(self,config):
        self.config = config
        self.vision_llm = init_chat_model(model=config.get("vision_llm","gpt-4o-mini"),temperature=0)  # Faster for captions
        self.text_llm = init_chat_model(model=config.get("text_llm","gpt-4.1"),temperature=0)
        # self.question_prompt = self._create_question_prompt()

        #extract pdf chunks
    def extract_pdf(self, pdf_path: str) -> List[ContentBlock]:
        """Extract PDF content and organize into ContentBlocks"""
        chunks = partition_pdf(
            filename=pdf_path,
            infer_table_structure=True,
            strategy="hi_res",
            extract_image_block_types=["Image"],
            extract_image_block_to_payload=True,
            chunking_strategy="by_title",
            max_characters=15000,
            combine_text_under_n_chars=3000,
            new_after_n_chars=8000,
            overlap=200,
        )
        
        content_blocks = []
        for idx, chunk in enumerate(chunks):
            block = ContentBlock()
            block.chunk_index = idx
            
            # All chunks get text content
            block.text_content = str(chunk)
            
            # Handle different chunk types for additional processing
            if "CompositeElement" in str(type(chunk)):
                # Extract images and generate captions immediately  
                block.image_captions = self._extract_images_from_chunk(chunk)
                # CompositeElements might also contain tables within them
                block.related_tables.extend(self._extract_tables_from_chunk(chunk))
                
            elif "Table" in str(type(chunk)):
                # This chunk IS a table - store the table object
                block.related_tables = [chunk]
            
            # Create combined context using existing method
            block.combined_context = self._combine_context(block)
            
            content_blocks.append(block)
        
        return content_blocks
    def enrich_content_blocks(self, content_blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Enrich content blocks with additional metadata and processing"""
        for block in content_blocks:
            block.combined_context = self._combine_context(block)
            block.questions = self._generate_questions(block)
        return content_blocks

    def _combine_context(self, block: ContentBlock) -> str:
        """Combine text, image captions, and table descriptions into a single context string"""
        components = [block.text_content]
        if block.image_captions:
            components.append("\n".join(block.image_captions))
        if block.table_descriptions:
            components.append("\n".join(block.table_descriptions))
        return "\n\n".join(components)
    def _generate_questions(self, block: ContentBlock) -> List[Question]:
        """Generate structured questions for a content block"""
        # Create structured question generation prompt
        question_prompt_template = """
You are an expert educational assessment designer. Generate comprehensive questions based on the provided content.

Content: {content}

Generate exactly:
- 3 Long-answer questions (5-10 minutes each)
- 5 Multiple-choice questions (1-3 minutes each)

Follow Bloom's Taxonomy distribution:
- Remember (25%): 2 questions - definitions, facts, recall
- Understand (25%): 2 questions - explain, summarize, interpret
- Apply (25%): 2 questions - solve problems, use knowledge
- Analyze (15%): 1 question - break down, examine relationships
- Evaluate (10%): 1 question - judge, critique, assess

For Long Answer Questions:
- Provide 3-4 key points expected in the answer
- Set appropriate difficulty and time expectations

For Multiple Choice Questions:
- Provide exactly 4 options as separate strings
- Include one clearly correct answer
- Create plausible distractors
- Provide explanation for correct answer

Ensure questions reference images and tables when mentioned in the content.
"""

        # Create LangChain chain with structured output
        question_prompt = ChatPromptTemplate.from_template(question_prompt_template)
        question_chain = question_prompt | self.text_llm.with_structured_output(QuestionSet)
        
        try:
            # Generate structured questions
            question_set = question_chain.invoke({"content": block.combined_context})
            
            # Combine all questions into single list
            all_questions = question_set.long_answer_questions + question_set.multiple_choice_questions
            return all_questions
            
        except Exception as e:
            print(f"Failed to generate questions: {e}")
            return []

    def _extract_images_from_chunk(self, chunk) -> List[str]:
        """Extract images from chunk and generate captions immediately"""
        captions = []
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            for el in chunk.metadata.orig_elements:
                if "Image" in str(type(el)):
                    if hasattr(el.metadata, 'image_base64') and el.metadata.image_base64:
                        try:
                            # Validate base64 image
                            import base64
                            base64.b64decode(el.metadata.image_base64)
                            
                            # Generate caption immediately using GPT-4o
                            caption = self._generate_image_caption(el.metadata.image_base64)
                            captions.append(caption)
                            print(f"Generated caption for image")
                            
                        except Exception as e:
                            print(f"Failed to process image: {e}")
                            continue
        return captions
    
    def _generate_image_caption(self, image_base64: str) -> str:
        """Generate caption for a single image using GPT-4o"""
        # Correct message format for LangChain vision models
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this educational image in detail. Focus on scientific concepts, diagrams, data, experimental setups, charts, or any educational content shown."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        try:
            response = self.vision_llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Failed to generate image caption: {e}")
            return "Image description unavailable"
            response = self.vision_llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Failed to generate image caption: {e}")
            return "Image description unavailable"
    
    def _extract_tables_from_chunk(self, chunk) -> List:
        """Extract table objects from a CompositeElement chunk"""
        tables = []
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            for el in chunk.metadata.orig_elements:
                if "Table" in str(type(el)):
                    tables.append(el)
        return tables
    
    def generate_questions(self, content_blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Generate structured questions for all content blocks"""
        question_chain = self._create_question_chain()
        
        for block in content_blocks:
            if block.combined_context:
                try:
                    # Generate structured questions using QuestionSet
                    question_set: QuestionSet = question_chain.invoke({"content": block.combined_context})
                    
                    # Combine all questions into single list
                    block.questions = (
                        question_set.long_answer_questions + 
                        question_set.multiple_choice_questions
                    )
                    
                    print(f"✅ Generated {len(block.questions)} questions for chunk {block.chunk_index + 1}")
                    
                except Exception as e:
                    print(f"❌ Failed to generate questions for chunk {block.chunk_index + 1}: {e}")
                    block.questions = []
        
        return content_blocks

if __name__ == "__main__":
    print("🚀 Starting PDF Ingestion Pipeline Test...")
    
    config = {
        "vision_llm": "gpt-4o-mini",
        "text_llm": "gpt-4.1"
    }
    
    pipeline = IngestionPipeline(config)
    
    # Extract PDF content
    print("\n📄 Extracting PDF content...")
    content_blocks = pipeline.extract_pdf("chapter1.pdf")
    print(f"✅ Extracted {len(content_blocks)} content blocks")
    
    # Generate questions for first block only (for testing)
    if content_blocks:
        first_block = content_blocks[0]
        if first_block.combined_context:
            print(f"\n🤔 Generating questions for first block...")
            print(f"Block has {len(first_block.combined_context)} characters of context")
            
            # Generate questions for just the first block
            content_blocks_with_questions = pipeline.generate_questions([first_block])
            
            # Display the generated questions
            block = content_blocks_with_questions[0]
            if block.questions:
                print(f"\n🎯 GENERATED {len(block.questions)} QUESTIONS:")
                print("=" * 60)
                
                for i, question in enumerate(block.questions, 1):
                    print(f"\nQuestion {i}:")
                    print(f"Type: {question.question_type.value}")
                    print(f"Bloom Level: {question.bloom_level.value}")
                    print(f"Difficulty: {question.difficulty.value}")
                    print(f"Expected Time: {question.expected_time} minutes")
                    print(f"Text: {question.text}")
                    
                    if question.options:
                        print("Options:")
                        for j, option in enumerate(question.options):
                            print(f"  {chr(65+j)}) {option}")
                        print(f"Correct Answer: {question.correct_answer}")
                        if question.explanation:
                            print(f"Explanation: {question.explanation}")
                    else:
                        print(f"Key Points: {question.key_points}")
                    
                    print("-" * 50)
                    
                print(f"\n📊 Question Summary:")
                long_answers = [q for q in block.questions if q.question_type == QuestionType.LONG_ANSWER]
                mcqs = [q for q in block.questions if q.question_type == QuestionType.MULTIPLE_CHOICE]
                print(f"Long Answer Questions: {len(long_answers)}")
                print(f"Multiple Choice Questions: {len(mcqs)}")
                
            else:
                print("❌ No questions generated")
        else:
            print("❌ No combined context available for first block")
    else:
        print("❌ No content blocks extracted")


        

            
        
            