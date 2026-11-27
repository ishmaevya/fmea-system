import type { PropsWithChildren, ReactNode } from "react";
import { useAuth } from "./AuthContext";
import type { Role } from "../api/types";

interface RoleGateProps extends PropsWithChildren {
  roles: Role[];
  fallback?: ReactNode;
}

export function RoleGate({ roles, children, fallback = null }: RoleGateProps) {
  const { hasRole } = useAuth();
  return <>{hasRole(...roles) ? children : fallback}</>;
}
