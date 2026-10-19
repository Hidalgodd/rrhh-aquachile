import { api } from "../api.js";

export const request = (path, method = "GET", data) =>
  api(path, { method, ...(data === undefined ? {} : { body: JSON.stringify(data) }) });
export const localDateInput = () => {
  const date = new Date();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
};
export const dateText = (value) =>
  value ? new Date(`${String(value).slice(0, 10)}T12:00:00`).toLocaleDateString("es-CL") : "—";
export const dayCountText = (value) => `${value} ${value === 1 ? "día" : "días"}`;
export const money = (value) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(value || 0);
export const initials = (name = "") =>
  name.trim().split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase();
