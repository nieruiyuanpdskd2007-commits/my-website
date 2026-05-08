export default function SVDImageCompressionPost() {
  return (
    <main className="min-h-screen bg-white px-8 py-20 text-black">
      <article className="mx-auto max-w-3xl">
        <p className="text-sm uppercase tracking-[0.3em] text-gray-500">
          Math Notes
        </p>

        <h1 className="mt-6 text-4xl font-bold leading-tight">
          How SVD Enables Image Compression
        </h1>

        <p className="mt-4 text-gray-500">2026-05-08</p>

        <div className="mt-10 space-y-8 text-lg leading-8 text-gray-700">
          <section>
            <h2 className="text-2xl font-semibold text-black">
              1. What is SVD?
            </h2>
            <p className="mt-3">
              Singular value decomposition factorizes a matrix into three
              matrices: A = UΣVᵀ. The singular values in Σ describe how much
              information is preserved along different directions.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-black">
              2. Images as Matrices
            </h2>
            <p className="mt-3">
              A grayscale image can be represented as a matrix where each entry
              corresponds to pixel intensity. Compressing the image becomes a
              problem of approximating this matrix with fewer numbers.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-black">
              3. Low-rank Approximation
            </h2>
            <p className="mt-3">
              By keeping only the largest singular values and discarding the
              smaller ones, we can approximate the original image using a
              lower-rank matrix. This reduces storage while preserving the main
              visual structure.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-black">
              4. Why Compression Works
            </h2>
            <p className="mt-3">
              Many images contain redundant information. The largest singular
              values usually capture the most important patterns, while smaller
              singular values often represent fine details or noise.
            </p>
          </section>
        </div>
      </article>
    </main>
  );
}