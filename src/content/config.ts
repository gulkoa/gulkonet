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

// one YAML file per paper in src/content/papers; listed on the home page, newest first
const papersCollection = defineCollection({
  type: 'data',
  schema: z.object({
    title: z.string(),
    authors: z.array(z.string()).min(1),
    note: z.string().optional(), // shown after the authors, e.g. the advisor of a thesis
    venue: z.string(),
    date: z.string(), // publication date, only used for sorting
    description: z.string(),
    links: z.array(z.object({ label: z.string(), href: z.string() })).min(1), // the first one is also the title link
  }),
});

export const collections = {
  'projects': projectsCollection,
  'blog': blogCollection,
  'papers': papersCollection
};