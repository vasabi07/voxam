"""
VLM/OCR Model Evaluation Package

This package provides tools to evaluate various VLM (Vision-Language Model)
and OCR models for document ingestion in the VOXAM platform.

Modules:
- local_evaluate: Test models that run locally (Granite-Docling)
- deepinfra_evaluate: Test models via DeepInfra API (olmOCR-2, Qwen-VL)
- replicate_evaluate: Test models via Replicate API (dots.ocr, Marker)
- runpod_evaluate: Deploy and test models on RunPod serverless
- compare_models: Aggregate results and generate recommendations
"""
