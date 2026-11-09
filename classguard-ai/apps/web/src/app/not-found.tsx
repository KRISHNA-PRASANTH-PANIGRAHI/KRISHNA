import Link from "next/link";

export default function NotFound() {
  return (
    <main className="not-found">
      <h1>This page isn’t here.</h1>
      <p>Return to your ClassGuard workspace to continue.</p>
      <Link className="button primary" href="/">
        Go to dashboard
      </Link>
    </main>
  );
}
