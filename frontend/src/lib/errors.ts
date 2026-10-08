import { ApiError } from "./api";
import type { Dictionary } from "./i18n";

/** Turns an API failure into a message that says what happened and what to do. */
export function errorMessage(error: unknown, t: Dictionary): string {
  if (!(error instanceof ApiError)) return t.errorGeneric;
  switch (error.status) {
    case 0:
      return t.errorNetwork;
    case 404:
      return t.errorExpired;
    case 413:
      return t.errorTooLarge;
    case 415:
      return t.errorUnsupported;
    case 422:
      return t.errorNoText;
    case 429:
      return t.errorRateLimit;
    case 503:
      return t.errorBusy;
    case 409:
      return t.fileLimit;
    default:
      return t.errorGeneric;
  }
}
