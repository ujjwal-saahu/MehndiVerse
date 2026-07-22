// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { DataTable, type DataTableColumn } from "./data-table";

interface Row {
  id: string;
  name: string;
  email: string;
}

const columns: DataTableColumn<Row>[] = [
  { key: "name", header: "Name", render: (row) => row.name },
  { key: "email", header: "Email", render: (row) => row.email },
];

const rows: Row[] = [
  { id: "1", name: "Asha Verma", email: "asha@example.com" },
  { id: "2", name: "Rohan Shah", email: "rohan@example.com" },
];

describe("DataTable", () => {
  it("renders column headers and row data", () => {
    render(<DataTable columns={columns} rows={rows} getRowKey={(row) => row.id} />);

    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    expect(screen.getByText("Asha Verma")).toBeInTheDocument();
    expect(screen.getByText("rohan@example.com")).toBeInTheDocument();
  });

  it("renders skeleton rows while loading instead of real data", () => {
    render(<DataTable columns={columns} rows={rows} getRowKey={(row) => row.id} isLoading />);

    expect(screen.queryByText("Asha Verma")).not.toBeInTheDocument();
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });

  it("renders an empty state when there are no rows", () => {
    render(
      <DataTable
        columns={columns}
        rows={[]}
        getRowKey={(row) => row.id}
        emptyTitle="No users yet"
        emptyMessage="Invite your first user to get started."
      />,
    );

    expect(screen.getByText("No users yet")).toBeInTheDocument();
    expect(screen.getByText("Invite your first user to get started.")).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <DataTable columns={columns} rows={rows} getRowKey={(row) => row.id} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders a plain header when a column has no sortKey", () => {
    render(<DataTable columns={columns} rows={rows} getRowKey={(row) => row.id} />);
    expect(screen.queryByRole("button", { name: "Name" })).not.toBeInTheDocument();
  });

  it("renders a clickable, accessible sort control for a sortable column", () => {
    const sortableColumns: DataTableColumn<Row>[] = [
      { key: "name", header: "Name", sortKey: "name", render: (row) => row.name },
      { key: "email", header: "Email", render: (row) => row.email },
    ];
    const onSortChange = vi.fn();
    render(
      <DataTable
        columns={sortableColumns}
        rows={rows}
        getRowKey={(row) => row.id}
        sortBy="name"
        sortDir="asc"
        onSortChange={onSortChange}
      />,
    );

    const header = screen.getByRole("columnheader", { name: "Name" });
    expect(header).toHaveAttribute("aria-sort", "ascending");

    fireEvent.click(screen.getByRole("button", { name: "Name" }));
    expect(onSortChange).toHaveBeenCalledWith("name");
  });

  it("has no detectable accessibility violations with sortable columns", async () => {
    const sortableColumns: DataTableColumn<Row>[] = [
      { key: "name", header: "Name", sortKey: "name", render: (row) => row.name },
      { key: "email", header: "Email", render: (row) => row.email },
    ];
    const { container } = render(
      <DataTable
        columns={sortableColumns}
        rows={rows}
        getRowKey={(row) => row.id}
        sortBy="name"
        sortDir="asc"
        onSortChange={vi.fn()}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
