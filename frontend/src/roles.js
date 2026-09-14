export const ROLE_LABELS = {
  ADMIN: "Administrador",
  ANALISTA: "Analista",
  REVISOR: "Revisor",
};

export function canMutate(user) {
  return user?.role === "ADMIN" || user?.role === "ANALISTA";
}

export function isAdmin(user) {
  return user?.role === "ADMIN";
}
