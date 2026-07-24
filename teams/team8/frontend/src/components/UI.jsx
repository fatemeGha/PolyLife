import {
  AlertCircle,
  CheckCircle2,
  Image as ImageIcon,
  LoaderCircle,
  Search,
} from "lucide-react";

export function Avatar({ profile, size = "medium" }) {
  const name = profile?.display_name || profile?.username || "کاربر";
  const initials = name.trim().slice(0, 2);
  return profile?.avatar_url ? (
    <img className={`avatar avatar--${size}`} src={profile.avatar_url} alt="" />
  ) : (
    <span className={`avatar avatar--${size} avatar--fallback`} aria-hidden="true">
      {initials}
    </span>
  );
}

export function Loading({ label = "در حال دریافت اطلاعات…" }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={24} />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  icon: Icon = ImageIcon,
  title,
  description,
  action,
}) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon">
        <Icon size={27} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function SearchField({ value, onChange, placeholder, onSubmit }) {
  return (
    <form className="search-field" onSubmit={onSubmit}>
      <Search size={19} aria-hidden="true" />
      <label className="sr-only" htmlFor="global-search">
        جستجو
      </label>
      <input
        id="global-search"
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
      <button type="submit" className="text-button">
        جستجو
      </button>
    </form>
  );
}

export function Toast({ toast, onDismiss }) {
  if (!toast) return null;
  const Icon = toast.type === "error" ? AlertCircle : CheckCircle2;
  return (
    <button
      type="button"
      className={`toast toast--${toast.type || "success"}`}
      onClick={onDismiss}
      aria-live="polite"
    >
      <Icon size={20} />
      <span>{toast.message}</span>
    </button>
  );
}

export function ErrorNotice({ message, retry }) {
  return (
    <div className="notice notice--error" role="alert">
      <AlertCircle size={20} />
      <span>{message}</span>
      {retry && (
        <button type="button" className="text-button" onClick={retry}>
          تلاش دوباره
        </button>
      )}
    </div>
  );
}

export function Stars({ value = 0, onChange, label = "امتیاز محتوا" }) {
  return (
    <div className="stars" aria-label={label}>
      {[1, 2, 3, 4, 5].map((score) => (
        <button
          key={score}
          type="button"
          className={score <= value ? "star star--active" : "star"}
          onClick={() => onChange?.(score)}
          aria-label={`${score} ستاره`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

