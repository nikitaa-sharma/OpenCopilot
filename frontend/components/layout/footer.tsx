import { GitPullRequest, Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-border/40 bg-card/40 py-8 md:py-12">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <GitPullRequest className="h-4 w-4" />
            </div>
            <span className="font-semibold text-sm">OpenSource Copilot</span>
            <span className="text-xs text-muted-foreground">— AI Contribution Assistant</span>
          </div>

          <p className="text-xs text-muted-foreground text-center md:text-right">
            Built for developers to accelerate open-source contributions.
          </p>
        </div>
      </div>
    </footer>
  );
}
