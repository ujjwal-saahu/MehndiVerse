import { execFileSync } from "node:child_process";

const CONTAINER = process.env.E2E_POSTGRES_CONTAINER ?? "mehndidesignapp-postgres-1";
const DB_USER = process.env.E2E_POSTGRES_USER ?? "mehndiverse";
const DB_NAME = process.env.E2E_POSTGRES_DB ?? "mehndiverse";

/** Runs `sql` inside the local Postgres container via `docker exec` — the
 * fastest way to seed a role/state that the backend's own auto-provisioning
 * (`get_current_user`, which always creates a plain `customer`) can't
 * produce. Only for local/CI E2E fixtures, never anything user-facing. */
function runSql(sql: string): void {
  execFileSync(
    "docker",
    ["exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-v", "ON_ERROR_STOP=1", "-c", sql],
    { stdio: "pipe" },
  );
}

export function seedUser(params: {
  id: string;
  email: string;
  role: "customer" | "artist" | "moderator" | "administrator" | "super_administrator";
  displayName?: string;
}): void {
  const { id, email, role, displayName } = params;
  runSql(
    `INSERT INTO users (id, email, role, status) VALUES ('${id}', '${email}', '${role}', 'active') ` +
      `ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role`,
  );
  runSql(
    `INSERT INTO profiles (user_id, display_name) VALUES ('${id}', '${displayName ?? email}') ` +
      `ON CONFLICT (user_id) DO UPDATE SET display_name = EXCLUDED.display_name`,
  );
}

export function seedArtistProfile(params: { userId: string; id: string }): void {
  runSql(
    `INSERT INTO artist_profiles ` +
      `(id, user_id, verification_status, is_accepting_bookings, rating_average, rating_count) ` +
      `VALUES ('${params.id}', '${params.userId}', 'approved', true, 0, 0) ` +
      `ON CONFLICT (id) DO NOTHING`,
  );
}
