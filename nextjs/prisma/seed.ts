import { PrismaClient } from '../app/generated/prisma/index.js';

const prisma = new PrismaClient();

/**
 * Seed script for SubscriptionPlan table
 * 
 * Run with: npx ts-node prisma/seed.ts
 * Or: npx prisma db seed (after configuring package.json)
 * 
 * NOTE: Update razorpayPlanId values after creating plans in Razorpay Dashboard
 */

const plans = [
    {
        name: 'starter',
        displayName: 'Starter Plan',
        razorpayPlanId: 'plan_STARTER_PLACEHOLDER', // TODO: Replace with actual ID from Razorpay
        priceInr: 399,
        voiceMinutes: 150,
        chatMessages: 1000,
        pages: 100,  // More generous!
        isActive: true,
    },
    {
        name: 'pro',
        displayName: 'Pro Plan',
        razorpayPlanId: 'plan_PRO_PLACEHOLDER', // TODO: Replace with actual ID from Razorpay
        priceInr: 699,
        voiceMinutes: 300,
        chatMessages: 2000,
        pages: 300,  // More generous!
        isActive: true,
    },
    {
        name: 'unlimited',
        displayName: 'Unlimited Plan',
        razorpayPlanId: 'plan_UNLIMITED_PLACEHOLDER', // TODO: Replace with actual ID from Razorpay
        priceInr: 999,
        voiceMinutes: 600,
        chatMessages: 5000, // Practically unlimited
        pages: 500,  // More generous!
        isActive: true,
    },
];

async function main() {
    console.log('🌱 Seeding SubscriptionPlan table...\n');

    for (const plan of plans) {
        const created = await prisma.subscriptionPlan.upsert({
            where: { name: plan.name },
            update: plan,
            create: plan,
        });

        console.log(`✅ ${created.displayName}`);
        console.log(`   Price: ₹${created.priceInr}/month`);
        console.log(`   Voice: ${created.voiceMinutes} min`);
        console.log(`   Chat: ${created.chatMessages} messages`);
        console.log(`   Pages: ${created.pages}`);
        console.log(`   Razorpay ID: ${created.razorpayPlanId}`);
        console.log('');
    }

    console.log('🎉 Seeding complete!\n');
    console.log('⚠️  REMINDER: Replace PLACEHOLDER Razorpay plan IDs with actual IDs');
    console.log('   1. Go to Razorpay Dashboard → Subscriptions → Plans');
    console.log('   2. Create 3 plans (Starter ₹399, Pro ₹699, Unlimited ₹999)');
    console.log('   3. Update razorpayPlanId in this file');
    console.log('   4. Re-run: npx ts-node prisma/seed.ts');
}

main()
    .catch((e) => {
        console.error('❌ Seeding failed:', e);
        process.exit(1);
    })
    .finally(async () => {
        await prisma.$disconnect();
    });
