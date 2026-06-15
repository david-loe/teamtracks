export const SONG_KEYS = [
  { value: 0, label: "C" },
  { value: 1, label: "C#/Db" },
  { value: 2, label: "D" },
  { value: 3, label: "D#/Eb" },
  { value: 4, label: "E" },
  { value: 5, label: "F" },
  { value: 6, label: "F#/Gb" },
  { value: 7, label: "G" },
  { value: 8, label: "G#/Ab" },
  { value: 9, label: "A" },
  { value: 10, label: "A#/Bb" },
  { value: 11, label: "B" },
] as const;

export type SongKeyValue = (typeof SONG_KEYS)[number]["value"];

export function formatSongKey(key: number | null | undefined): string {
  if (key === null || key === undefined) return "tonartunabhaengig";
  return SONG_KEYS.find((songKey) => songKey.value === key)?.label ?? String(key);
}
