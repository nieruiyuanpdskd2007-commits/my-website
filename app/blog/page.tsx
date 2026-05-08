import Link from "next/link";

const posts = [
  {
    title: "Understanding DFS, BFS, UCS, and A*",
    date: "2026-05-08",
    description:
      "A concise note on classical search algorithms and their use in AI pathfinding problems.",
    href: "/blog/search-algorithms",
  },
  {
    title: "How SVD Enables Image Compression",
    date: "2026-05-08",
    description:
      "An intuitive explanation of singular value decomposition and low-rank approximation.",
    href: "/blog/svd-image-compression",
  },
];

export default function BlogPage() {
  return (
    <main className="min-h-screen bg-white px-8 py-20 text-black">
      <section className="mx-auto max-w-4xl">
        <p className="text-sm uppercase tracking-[0.3em] text-gray-500">
          Writing
        </p>

        <h1 className="mt-6 text-4xl font-bold">Blog</h1>

        <p className="mt-5 max-w-2xl text-lg leading-8 text-gray-600">
          Notes on artificial intelligence, mathematics, programming, and
          academic development.
        </p>

        <div className="mt-10 grid gap-6">
          {posts.map((post) => (
            <Link
              key={post.title}
              href={post.href}
              className="rounded-2xl border border-gray-200 p-6 transition hover:-translate-y-1 hover:shadow-md"
            >
              <p className="text-sm text-gray-500">{post.date}</p>
              <h2 className="mt-2 text-2xl font-semibold">{post.title}</h2>
              <p className="mt-4 leading-7 text-gray-600">
                {post.description}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}