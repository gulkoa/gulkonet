import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context: any) {
  // blog posts, newest first
  const posts = (await getCollection('blog')).sort(
    (a, b) => new Date(b.data.created).getTime() - new Date(a.data.created).getTime()
  );
  return rss({
    // `<title>` field in output xml
    title: 'Alex Gulko’s Blog',
    // `<description>` field in output xml
    description: 'Thoughts on software development, design, and other things.',
    // Pull in your project "site" from the endpoint context
    // https://docs.astro.build/en/reference/api-reference/#contextsite
    site: context.site,
    // Array of `<item>`s in output xml
    items: posts.map((post) => ({
      title: post.data.title,
      pubDate: new Date(post.data.created),
      description: post.data.description,
      categories: post.data.tags,
      link: `/blog/${post.slug}/`,
    })),
    // (optional) inject custom xml
    customData: `<language>en-us</language>`,
  });
}
