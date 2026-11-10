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

// a person on a paper: a name, or a name with a link to their website; a trailing * marks equal contribution
const person = z.union([z.string(), z.object({ name: z.string(), url: z.string() })]);

// one MDX file per paper in src/content/papers: the frontmatter feeds the home page list
// (newest first) and the body is the write-up shown on /papers/<slug>
const papersCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    authors: z.array(person).min(1),
    advisors: z.array(person).optional(), // shown after the authors as "Advised by ..."
    note: z.string().optional(), // free text shown after the authors
    venue: z.string(),
    date: z.string(), // publication date, used for sorting
    description: z.string(),
    links: z.array(z.object({ label: z.string(), href: z.string() })).default([]),
    image: z.string().optional(), // social card in src/assets, the portrait is used without one
  }),
});

export const collections = {
  'projects': projectsCollection,
  'blog': blogCollection,
  'papers': papersCollection
};