// A small hand-rolled icon set (inline SVG, stroke-based, 1.5px) so the
// redesign doesn't need an icon library dependency. Every icon used across
// the app is defined once here and reused everywhere.

export type IconProps = { className?: string };

function base(paths: React.ReactNode) {
  return function Icon({ className = "h-5 w-5" }: IconProps) {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        aria-hidden="true"
      >
        {paths}
      </svg>
    );
  };
}

export const DashboardIcon = base(
  <>
    <rect x="3" y="3" width="7" height="9" rx="1.5" />
    <rect x="14" y="3" width="7" height="5" rx="1.5" />
    <rect x="14" y="12" width="7" height="9" rx="1.5" />
    <rect x="3" y="16" width="7" height="5" rx="1.5" />
  </>
);

export const ListIcon = base(
  <>
    <path d="M8 6h13" />
    <path d="M8 12h13" />
    <path d="M8 18h13" />
    <path d="M3 6h.01" />
    <path d="M3 12h.01" />
    <path d="M3 18h.01" />
  </>
);

export const SparkleIcon = base(
  <>
    <path d="M12 3v3" />
    <path d="M12 18v3" />
    <path d="M3 12h3" />
    <path d="M18 12h3" />
    <path d="M5.6 5.6l2.1 2.1" />
    <path d="M16.3 16.3l2.1 2.1" />
    <path d="M18.4 5.6l-2.1 2.1" />
    <path d="M7.7 16.3l-2.1 2.1" />
    <circle cx="12" cy="12" r="2.5" />
  </>
);

export const ShieldIcon = base(
  <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" />
);

export const AlertIcon = base(
  <>
    <path d="M12 4l9 16H3l9-16z" />
    <path d="M12 10v4" />
    <path d="M12 17h.01" />
  </>
);

export const CheckCircleIcon = base(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M8.5 12.3l2.4 2.4 4.6-5.2" />
  </>
);

export const XCircleIcon = base(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9.5l5 5" />
    <path d="M14.5 9.5l-5 5" />
  </>
);

export const ClockIcon = base(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3.5 2" />
  </>
);

export const ArrowDownIcon = base(<path d="M12 4v16M6 14l6 6 6-6" />);

export const ArrowRightIcon = base(<path d="M4 12h16M14 6l6 6-6 6" />);

export const ChevronDownIcon = base(<path d="M6 9l6 6 6-6" />);

export const SearchIcon = base(
  <>
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4.3-4.3" />
  </>
);

export const CoinsIcon = base(
  <>
    <ellipse cx="9" cy="7" rx="6" ry="3.3" />
    <path d="M3 7v6c0 1.8 2.7 3.3 6 3.3s6-1.5 6-3.3V7" />
    <path d="M15 10.2c2.9.3 5 1.6 5 3.1 0 1.8-2.7 3.3-6 3.3-2 0-3.8-.6-4.9-1.4" />
    <path d="M14 17v.2c0 1.8-2.7 3.3-6 3.3s-6-1.5-6-3.3V11" />
  </>
);

export const TrendUpIcon = base(
  <>
    <path d="M4 16l6-6 4 4 6-8" />
    <path d="M15 6h5v5" />
  </>
);

export const UsersIcon = base(
  <>
    <circle cx="9" cy="8" r="3.2" />
    <path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" />
    <circle cx="17.5" cy="9" r="2.4" />
    <path d="M15.5 14.2c2.7.3 5 2 5 5.8" />
  </>
);

export const CpuIcon = base(
  <>
    <rect x="7" y="7" width="10" height="10" rx="1.5" />
    <rect x="10" y="2.5" width="4" height="3" rx="0.5" />
    <rect x="10" y="18.5" width="4" height="3" rx="0.5" />
    <rect x="2.5" y="10" width="3" height="4" rx="0.5" />
    <rect x="18.5" y="10" width="3" height="4" rx="0.5" />
  </>
);

export const MagnifierScanIcon = base(
  <>
    <circle cx="10.5" cy="10.5" r="6.5" />
    <path d="M20 20l-4.8-4.8" />
    <path d="M10.5 7.5v6" />
    <path d="M7.5 10.5h6" />
  </>
);

export const TargetIcon = base(
  <>
    <circle cx="12" cy="12" r="8.5" />
    <circle cx="12" cy="12" r="4.5" />
    <circle cx="12" cy="12" r="0.6" fill="currentColor" />
  </>
);

export const GaugeIcon = base(
  <>
    <path d="M4 15a8 8 0 1 1 16 0" />
    <path d="M12 15l3.5-4.5" />
    <path d="M12 15h.01" />
  </>
);

export const PlayIcon = base(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M10 8.5l6 3.5-6 3.5v-7z" />
  </>
);

export const MenuIcon = base(
  <>
    <path d="M4 7h16" />
    <path d="M4 12h16" />
    <path d="M4 17h16" />
  </>
);

export const CloseIcon = base(
  <>
    <path d="M6 6l12 12" />
    <path d="M18 6L6 18" />
  </>
);

export const RefreshIcon = base(
  <>
    <path d="M4 12a8 8 0 0 1 13.7-5.7L20 9" />
    <path d="M20 4v5h-5" />
    <path d="M20 12a8 8 0 0 1-13.7 5.7L4 15" />
    <path d="M4 20v-5h5" />
  </>
);
