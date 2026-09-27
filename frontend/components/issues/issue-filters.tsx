"use client";

import { Search, Filter, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export type FilterCategory =
  | "All"
  | "Beginner"
  | "Intermediate"
  | "Advanced"
  | "Bug"
  | "Enhancement"
  | "Documentation"
  | "Good First Issue";

interface IssueFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  activeFilter: FilterCategory;
  onFilterChange: (filter: FilterCategory) => void;
  totalCount: number;
}

const FILTER_OPTIONS: FilterCategory[] = [
  "All",
  "Beginner",
  "Intermediate",
  "Advanced",
  "Good First Issue",
  "Documentation",
  "Enhancement",
  "Bug",
];

export function IssueFilters({
  searchQuery,
  onSearchChange,
  activeFilter,
  onFilterChange,
  totalCount,
}: IssueFiltersProps) {
  return (
    <div className="space-y-4 mb-6">
      {/* Search Input Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search issues by title, label, or skill..."
            className="pl-9 h-10 bg-secondary/30 text-xs border-border"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <div className="flex items-center space-x-2 text-xs text-muted-foreground self-start sm:self-auto font-mono">
          <span>Showing {totalCount} demonstration issues</span>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap items-center gap-1.5 pt-1">
        <div className="flex items-center space-x-1.5 text-xs text-muted-foreground mr-1">
          <Filter className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Filter:</span>
        </div>
        {FILTER_OPTIONS.map((filter) => {
          const isActive = activeFilter === filter;
          return (
            <button
              key={filter}
              type="button"
              onClick={() => onFilterChange(filter)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground border border-border/80"
              }`}
            >
              {filter}
            </button>
          );
        })}
      </div>
    </div>
  );
}
