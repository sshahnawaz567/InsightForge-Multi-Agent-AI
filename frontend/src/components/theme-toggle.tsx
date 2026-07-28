import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("light", light);
  }, [light]);

  return (
    <button
      type="button"
      aria-label={light ? "Switch to dark mode" : "Switch to light mode"}
      onClick={() => setLight((v) => !v)}
      className="glass flex size-9 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground"
    >
      {light ? <Moon className="size-4" /> : <Sun className="size-4" />}
    </button>
  );
}
