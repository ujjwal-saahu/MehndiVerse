import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col items-center gap-6 px-4 py-24 text-center sm:px-6">
      <h1 className="font-display text-4xl font-semibold text-text-primary sm:text-5xl">
        Discover mehndi artistry, for every occasion
      </h1>
      <p className="max-w-2xl text-lg text-text-secondary">
        Browse bridal and everyday mehndi designs, connect with trusted artists, and book your next
        appointment — all in one place.
      </p>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/discover"
          className="rounded-md bg-primary px-6 py-3 font-medium text-text-on-primary hover:bg-primary-hover"
        >
          Explore designs
        </Link>
        <Link
          href="/register"
          className="rounded-md border border-border px-6 py-3 font-medium text-text-primary hover:bg-surface-variant"
        >
          Create an account
        </Link>
      </div>
    </div>
  );
}
