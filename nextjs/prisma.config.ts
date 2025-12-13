import { defineConfig } from 'prisma/config';

export default defineConfig({
  datasource: {
    // The provider is still defined in schema.prisma
    url: process.env.DATABASE_URL ?? '',
  },
});
