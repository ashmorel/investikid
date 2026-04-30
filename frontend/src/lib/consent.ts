export const EU_COUNTRIES_16: ReadonlySet<string> = new Set([
  'IE', 'NL', 'DE', 'LU', 'SK', 'HR',
]);

export function consentThreshold(countryCode: string): 13 | 16 {
  return EU_COUNTRIES_16.has(countryCode) ? 16 : 13;
}

export function ageInYears(dob: Date, today: Date): number {
  let age = today.getFullYear() - dob.getFullYear();
  const beforeBirthday =
    today.getMonth() < dob.getMonth() ||
    (today.getMonth() === dob.getMonth() && today.getDate() < dob.getDate());
  if (beforeBirthday) age -= 1;
  return age;
}

export function needsParentalConsent(dob: Date, countryCode: string, today: Date): boolean {
  return ageInYears(dob, today) < consentThreshold(countryCode);
}
