import ar from "./locales/ar.json";
import en from "./locales/en.json";
import hi from "./locales/hi.json";
import ur from "./locales/ur.json";
import { DEFAULT_LOCALE, type Locale } from "./config";

export type Messages = typeof en;

export const translations: Record<Locale, Messages> = { en, hi, ur, ar };

type Primitive = string | number;

function readPath(messages: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((node, key) => {
    if (node && typeof node === "object" && key in node) {
      return (node as Record<string, unknown>)[key];
    }
    return undefined;
  }, messages);
}

function interpolate(template: string, params?: Record<string, Primitive>): string {
  if (!params) return template;
  return template.replace(/\{\{(\w+)\}\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match,
  );
}

/** Looks up a dot-path key (e.g. `"auth.login.title"`) in `locale`'s
 * catalog, falling back to `DEFAULT_LOCALE` and then to the key itself so a
 * missing translation degrades to visible-but-not-crashing rather than a
 * blank string. */
export function translate(locale: Locale, key: string, params?: Record<string, Primitive>): string {
  const value =
    readPath(translations[locale], key) ?? readPath(translations[DEFAULT_LOCALE], key) ?? key;
  return interpolate(String(value), params);
}
