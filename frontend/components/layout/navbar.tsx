"use client";

import { useState } from "react";
import Link from "next/link";
import { Code2, Github, Menu, X, User, LogIn, LogOut, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth-context";

import { ThemeToggle } from "@/components/layout/theme-toggle";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  const navLinks = [
    { name: "Analyze", href: "#analyzer" },
    { name: "Overview", href: "#overview" },
    { name: "Issues", href: "#issues" },
    { name: "Recommendations", href: "#recommendations" },
    { name: "Guide", href: "#guide" },
    { name: "AI Chat", href: "#chat" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/90 backdrop-blur-md">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center space-x-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/25 text-primary group-hover:bg-primary/20 transition-colors">
            <Code2 className="h-5 w-5" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-base sm:text-lg tracking-tight">OpenSource Copilot</span>
            <Badge variant="outline" className="hidden sm:inline-flex text-[10px] py-0 px-1.5 font-mono text-muted-foreground">
              v0.1 UI
            </Badge>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-6 text-sm font-medium text-muted-foreground">
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              className="hover:text-foreground transition-colors py-1"
            >
              {link.name}
            </a>
          ))}
        </nav>

        {/* Right Action & Mobile Toggle */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Theme Switcher Toggle */}
          <ThemeToggle />

          {/* Auth State Actions */}
          {isLoading ? (
            <div className="h-8 w-8 flex items-center justify-center">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : isAuthenticated && user ? (
            <div className="flex items-center space-x-2">
              <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-secondary/60 border border-border/60 text-xs">
                <User className="h-3.5 w-3.5 text-primary" />
                <span className="font-medium max-w-[120px] truncate text-foreground">
                  {user.display_name || user.email}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => logout()}
                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                title="Log out"
              >
                <LogOut className="h-3.5 w-3.5 sm:mr-1" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5">
              <Link href="/login">
                <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs">
                  <LogIn className="h-3.5 w-3.5 mr-1" />
                  <span>Log In</span>
                </Button>
              </Link>
              <Link href="/register">
                <Button size="sm" className="h-8 px-3 text-xs">
                  Sign Up
                </Button>
              </Link>
            </div>
          )}

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center space-x-1.5 text-xs font-medium text-foreground bg-secondary/80 hover:bg-secondary border border-border px-2.5 py-1.5 rounded-md transition-colors shadow-sm"
          >
            <Github className="h-3.5 w-3.5" />
            <span>GitHub</span>
          </a>

          <button
            type="button"
            className="md:hidden p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-card/95 backdrop-blur-md px-4 py-4 space-y-2 animate-in slide-in-from-top-2 duration-200">
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            >
              {link.name}
            </a>
          ))}
          <div className="pt-2 border-t border-border/60">
            {isAuthenticated && user ? (
              <div className="flex items-center justify-between px-3 py-2">
                <div className="text-xs">
                  <p className="font-medium text-foreground">{user.display_name}</p>
                  <p className="text-muted-foreground">{user.email}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="text-xs"
                >
                  <LogOut className="h-3.5 w-3.5 mr-1" />
                  Logout
                </Button>
              </div>
            ) : (
              <div className="flex space-x-2 px-3 pt-1">
                <Link href="/login" className="flex-1" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full text-xs">
                    Log In
                  </Button>
                </Link>
                <Link href="/register" className="flex-1" onClick={() => setMobileMenuOpen(false)}>
                  <Button size="sm" className="w-full text-xs">
                    Sign Up
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

