import { defineConfig } from 'prisma/config';
import dotenv from 'dotenv';

dotenv.config();

export default defineConfig({
  datasource: {
    // The provider is still defined in schema.prisma
    url: process.env.DATABASE_URL ?? '',
  },
});
