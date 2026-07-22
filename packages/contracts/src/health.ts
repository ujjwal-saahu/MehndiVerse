export type ServiceStatus = "ok" | "degraded";

export interface ServiceHealth {
  status: ServiceStatus;
  service: string;
}
