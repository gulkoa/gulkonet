// import { glob } from 'astro/loaders';
import { z, defineCollection } from 'astro:content';

const projectsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    created: z.string(),
    image: z.string(),
    color: z.string().optional(),
    secondaryColor: z.string().optional(),
    tokens: z.array(z.string()).optional(),
    tags: z.array(z.string()).optional(),
    font: z.string().optional(),
    featured: z.boolean().optional(), // false keeps a project off the home page gallery
  }),
});

const blogCollection = defineCollection({
  type: 'content',
  // loader: glob({ pattern: "**/*.mdx", base: "./src/content/blog" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    created: z.string(),
    updated: z.string().optional(),
    image: z.string(),
    color: z.string().optional(),
    secondaryColor: z.string().optional(),
    tokens: z.array(z.string()).optional(),
    tags: z.array(z.string()).optional(),
    font: z.string().optional(),
  }),
});

export const collections = {
  'projects': projectsCollection,
  'blog': blogCollection
};