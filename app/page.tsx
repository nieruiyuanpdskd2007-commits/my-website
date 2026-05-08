export default function Home() {
  return (
    <main className="min-h-screen bg-white px-8 py-20 text-black">
      <section className="mx-auto max-w-4xl">
        <p className="text-sm uppercase tracking-[0.3em] text-gray-500">
          Personal Website
        </p>

        <h1 className="mt-6 text-5xl font-bold leading-tight">
          Ruiyuan&apos;s Digital Garden
        </h1>

        <p className="mt-6 max-w-2xl text-lg leading-8 text-gray-600">
          I am an undergraduate student at Nanjing University majoring in
          Intelligent Science and Technology. My interests include artificial
          intelligence, machine learning, computer vision, and intelligent
          systems.
        </p>

        <div className="mt-10 flex gap-4">
          <a
            href="/projects"
            className="rounded-full bg-black px-6 py-3 text-sm font-medium text-white"
          >
            View Projects
          </a>

          <a
            href="/blog"
            className="rounded-full border border-gray-300 px-6 py-3 text-sm font-medium"
          >
            Read Blog
          </a>
        </div>
      </section>
    </main>
  );
}