import { LogoutButton } from "./logout-button";

interface HeaderProps {
  email: string;
  role: string;
  onOpenSidebar?: () => void;
}

export function Header({ email, role, onOpenSidebar }: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 sm:px-6">
      <div className="flex items-center gap-3">
        {onOpenSidebar ? (
          <button
            type="button"
            onClick={onOpenSidebar}
            aria-label="Open navigation menu"
            className="rounded-md p-2 hover:bg-surface-variant lg:hidden"
          >
            <span aria-hidden="true">&#9776;</span>
          </button>
        ) : null}
        <span className="font-display text-lg font-semibold text-primary">MehndiVerse Admin</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-text-primary">{email}</p>
          <p className="text-xs text-text-secondary">{role}</p>
        </div>
        <LogoutButton />
      </div>
    </header>
  );
}
