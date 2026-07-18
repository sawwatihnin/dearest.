import type { ReactNode } from "react";

export function FeatherIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`icon icon-feather ${className}`.trim()}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20.5 3.5c-4 0-13 2-15.5 9.5C3.6 17 4 20.5 4 20.5s3.5.4 7.5-1c7.5-2.5 9.5-11.5 9.5-15.5-.83.83-2.83.83-3 0Z" />
      <path d="M13.5 10.5 4.5 19.5" />
    </svg>
  );
}

function BaseIcon({
  className = "",
  children
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <svg
      className={`icon ${className}`.trim()}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function ThemeIcon({ className = "" }: { className?: string }) {
  return (
    <BaseIcon className={className}>
      <path d="M19 5c-4.6.1-8.45 2.6-10.82 6.09C6.39 13.73 5.3 16.58 5 19c2.42-.3 5.27-1.39 7.91-3.18C16.4 13.45 18.9 9.6 19 5Z" />
      <path d="M8 13c1.7-.3 3.26-1.12 4.38-2.33" />
    </BaseIcon>
  );
}

export function HeartOutlineIcon({ className = "" }: { className?: string }) {
  return (
    <BaseIcon className={className}>
      <path d="M12 20.5s-6.5-4.3-8.5-8.4C2 9 3.66 5.5 7.52 5.5c1.96 0 3.14.95 4.48 2.62 1.34-1.67 2.52-2.62 4.48-2.62C20.34 5.5 22 9 20.5 12.1 18.5 16.2 12 20.5 12 20.5Z" />
    </BaseIcon>
  );
}

export function TagIcon({ className = "" }: { className?: string }) {
  return (
    <BaseIcon className={className}>
      <path d="m13 5 6 6-8.5 8.5a2 2 0 0 1-2.83 0L3.5 15.33a2 2 0 0 1 0-2.83L12 4h1Z" />
      <circle cx="15.5" cy="8.5" r="1" fill="currentColor" stroke="none" />
    </BaseIcon>
  );
}

export function CompassIcon({ className = "" }: { className?: string }) {
  return (
    <BaseIcon className={className}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m15.5 8.5-2.2 6.3-4.8 1.7 2.2-6.3 4.8-1.7Z" />
    </BaseIcon>
  );
}

export function LockIcon({ className = "" }: { className?: string }) {
  return (
    <BaseIcon className={className}>
      <rect x="5.5" y="10.5" width="13" height="9" rx="2.2" />
      <path d="M8.5 10.5V8.2a3.5 3.5 0 1 1 7 0v2.3" />
      <path d="M12 14v2.5" />
    </BaseIcon>
  );
}

export function ShieldIcon({ className = "" }: { className?: string }) {
  return (
    <BaseIcon className={className}>
      <path d="M12 3.5 18.5 6v5.2c0 4.05-2.72 7.7-6.5 9.3-3.78-1.6-6.5-5.25-6.5-9.3V6L12 3.5Z" />
      <path d="m9.3 12.2 1.8 1.8 3.7-4" />
    </BaseIcon>
  );
}
