import { SystemStatus } from "./system-status";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-16">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">ReturnGuard</h1>
        <p className="text-zinc-600 dark:text-zinc-400">
          AI reviews clear-cut returns. A person owns every denial and every judgment call.
        </p>
      </header>
      <SystemStatus />
    </main>
  );
}
