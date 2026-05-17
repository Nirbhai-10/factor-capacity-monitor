import dataJson from "./data.json";
import type { Payload } from "./types";

export const data: Payload = dataJson as unknown as Payload;
