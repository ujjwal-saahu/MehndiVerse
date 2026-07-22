import { DataExportView } from "./data-export-view";

export const metadata = { title: "Data export | MehndiVerse" };

export default function DataExportPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Export your data</h1>
      <div className="mt-6">
        <DataExportView />
      </div>
    </div>
  );
}
