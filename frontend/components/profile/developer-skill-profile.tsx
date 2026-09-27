"use client";

import { useState, useEffect, useRef } from "react";
import { UserCheck, Plus, X, Sparkles, Check, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DeveloperSkillProfile } from "@/types";
import { getDeveloperSkillProfile, saveDeveloperSkillProfile } from "@/lib/api";
import { useAuth } from "@/context/auth-context";

const QUICK_SUGGESTIONS = {
  programming_languages: ["Python", "JavaScript", "TypeScript", "Go", "Rust", "C++", "Java"],
  frameworks: ["FastAPI", "React", "Next.js", "Django", "Flask", "Node.js", "Vue.js"],
  tools: ["Git", "Docker", "PostgreSQL", "Redis", "Kubernetes", "Pytest"],
  domains: ["Web Development", "AI", "Backend Development", "Frontend Development", "DevOps"],
  interests: ["Open Source", "Documentation", "Testing", "Performance", "Security"],
};

interface DeveloperSkillProfileProps {
  onProfileUpdated?: (profile: DeveloperSkillProfile) => void;
}

export function DeveloperSkillProfileComponent({ onProfileUpdated }: DeveloperSkillProfileProps) {
  const { user, isAuthenticated } = useAuth();
  const onProfileUpdatedRef = useRef(onProfileUpdated);
  useEffect(() => {
    onProfileUpdatedRef.current = onProfileUpdated;
  }, [onProfileUpdated]);

  const [profile, setProfile] = useState<DeveloperSkillProfile>({
    programming_languages: ["Python", "JavaScript"],
    frameworks: ["FastAPI", "React"],
    tools: ["Git", "Docker"],
    domains: ["Web Development", "AI"],
    experience_level: "beginner",
    interests: ["Open Source"],
  });

  const [inputStates, setInputStates] = useState<{ [key: string]: string }>({
    programming_languages: "",
    frameworks: "",
    tools: "",
    domains: "",
    interests: "",
  });

  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load existing profile from backend on mount or user change
  useEffect(() => {
    async function load() {
      try {
        const remote = await getDeveloperSkillProfile();
        // If remote has skills, use it
        if (
          remote.programming_languages.length > 0 ||
          remote.frameworks.length > 0 ||
          remote.tools.length > 0 ||
          remote.domains.length > 0 ||
          remote.interests.length > 0
        ) {
          setProfile(remote);
          onProfileUpdatedRef.current?.(remote);
        } else {
          // Check local storage fallback
          const local = localStorage.getItem("dev_skill_profile");
          if (local) {
            try {
              const parsed = JSON.parse(local);
              setProfile(parsed);
              onProfileUpdatedRef.current?.(parsed);
            } catch {
              // ignore json parse error
            }
          }
        }
      } catch (err) {
        setLoadError("Could not connect to profile service; using local settings.");
      }
    }
    load();
  }, [isAuthenticated, user?.id]);


  const handleAddSkill = (category: keyof Omit<DeveloperSkillProfile, "experience_level">, skillToAdd?: string) => {
    const raw = (skillToAdd || inputStates[category] || "").trim();
    if (!raw) return;

    // Check if already in list case-insensitively
    const exists = profile[category].some((s) => s.toLowerCase() === raw.toLowerCase());
    if (!exists) {
      const updatedList = [...profile[category], raw];
      setProfile((prev) => ({
        ...prev,
        [category]: updatedList,
      }));
    }

    setInputStates((prev) => ({
      ...prev,
      [category]: "",
    }));
  };

  const handleRemoveSkill = (category: keyof Omit<DeveloperSkillProfile, "experience_level">, skillToRemove: string) => {
    setProfile((prev) => ({
      ...prev,
      [category]: prev[category].filter((s) => s.toLowerCase() !== skillToRemove.toLowerCase()),
    }));
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    setSavedSuccess(false);
    try {
      const saved = await saveDeveloperSkillProfile(profile);
      setProfile(saved);
      localStorage.setItem("dev_skill_profile", JSON.stringify(saved));
      setSavedSuccess(true);
      onProfileUpdated?.(saved);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      // Local storage fallback if backend unreachable
      localStorage.setItem("dev_skill_profile", JSON.stringify(profile));
      setSavedSuccess(true);
      onProfileUpdated?.(profile);
      setTimeout(() => setSavedSuccess(false), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  const renderSkillSection = (
    label: string,
    category: keyof Omit<DeveloperSkillProfile, "experience_level">,
    suggestions: string[]
  ) => {
    const currentList = profile[category] || [];

    return (
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-foreground uppercase tracking-wider">
            {label}
          </label>
          <span className="text-[11px] text-muted-foreground">
            {currentList.length} added
          </span>
        </div>

        {/* Selected skills pills */}
        <div className="flex flex-wrap gap-1.5 min-h-[32px] p-2 rounded-lg bg-secondary/30 border border-border/50">
          {currentList.length === 0 && (
            <span className="text-xs text-muted-foreground/60 italic py-0.5">
              None added yet.
            </span>
          )}
          {currentList.map((skill) => (
            <span
              key={skill}
              className="inline-flex items-center gap-1.5 text-xs font-mono bg-primary/10 border border-primary/30 text-primary px-2.5 py-0.5 rounded-full"
            >
              <span>{skill}</span>
              <button
                type="button"
                onClick={() => handleRemoveSkill(category, skill)}
                className="hover:text-primary-foreground hover:bg-primary/80 rounded-full p-0.5 transition-colors"
                title={`Remove ${skill}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>

        {/* Add skill input + suggestions */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Input
              type="text"
              placeholder={`Add ${label.toLowerCase()}...`}
              value={inputStates[category]}
              onChange={(e) => setInputStates({ ...inputStates, [category]: e.target.value })}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddSkill(category);
                }
              }}
              className="h-8 text-xs font-mono"
            />
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => handleAddSkill(category)}
            className="h-8 px-2.5 text-xs shrink-0"
          >
            <Plus className="h-3.5 w-3.5 mr-1" />
            <span>Add</span>
          </Button>
        </div>

        {/* Quick Suggestions */}
        <div className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground pt-0.5">
          <span className="mr-1 text-[10px] uppercase font-semibold text-muted-foreground/80">Suggestions:</span>
          {suggestions
            .filter((s) => !currentList.some((c) => c.toLowerCase() === s.toLowerCase()))
            .slice(0, 5)
            .map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => handleAddSkill(category, s)}
                className="hover:text-primary hover:bg-primary/10 border border-border/40 px-1.5 py-0.5 rounded text-[10px] transition-colors"
              >
                +{s}
              </button>
            ))}
        </div>
      </div>
    );
  };

  return (
    <section id="developer-profile" className="py-8 border-t border-border/40 scroll-mt-16 bg-card/10">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Card className="border-border bg-card/90 shadow-xl overflow-hidden max-w-4xl mx-auto">
          <CardHeader className="p-6 border-b border-border/40 bg-secondary/15">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
                  <UserCheck className="h-3.5 w-3.5" />
                  <span>Personalized Recommendation Settings</span>
                </div>
                <CardTitle className="text-xl sm:text-2xl font-bold text-foreground">
                  Developer Skill Profile
                </CardTitle>
                <CardDescription className="text-xs mt-1">
                  Configure your skills and interests to generate personalized, grounded issue recommendations.
                </CardDescription>
                <div className="flex items-center gap-2 mt-1.5">
                  {isAuthenticated && user ? (
                    <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-500/10 text-[10px] gap-1 py-0.5 px-2 font-normal">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Synced to {user.email}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="border-border text-muted-foreground bg-secondary/40 text-[10px] gap-1 py-0.5 px-2 font-normal">
                      Guest Session (Sign in to persist across devices)
                    </Badge>
                  )}
                </div>
              </div>


              <div className="flex items-center gap-2">
                <Button
                  onClick={handleSaveProfile}
                  disabled={isSaving}
                  size="sm"
                  className="gap-1.5 shadow-sm text-xs font-medium"
                >
                  {isSaving ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Normalizing & Saving...</span>
                    </>
                  ) : savedSuccess ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span>Profile Saved!</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Save Profile</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Programming Languages */}
              {renderSkillSection(
                "Programming Languages",
                "programming_languages",
                QUICK_SUGGESTIONS.programming_languages
              )}

              {/* Frameworks & Libraries */}
              {renderSkillSection(
                "Frameworks & Libraries",
                "frameworks",
                QUICK_SUGGESTIONS.frameworks
              )}

              {/* Tools & Infrastructure */}
              {renderSkillSection(
                "Tools & Infrastructure",
                "tools",
                QUICK_SUGGESTIONS.tools
              )}

              {/* Domains & Focus Areas */}
              {renderSkillSection(
                "Domains & Focus Areas",
                "domains",
                QUICK_SUGGESTIONS.domains
              )}
            </div>

            {/* Bottom Row: Experience Level & Interests */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-border/40">
              {/* Experience Level */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-foreground uppercase tracking-wider block">
                  Experience Level
                </label>
                <div className="flex items-center gap-2">
                  {(["beginner", "intermediate", "advanced"] as const).map((level) => {
                    const isSelected = profile.experience_level === level;
                    return (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setProfile((p) => ({ ...p, experience_level: level }))}
                        className={`capitalize px-3 py-1.5 rounded-md text-xs font-medium border transition-all ${
                          isSelected
                            ? "bg-primary text-primary-foreground border-primary shadow-sm"
                            : "bg-secondary/40 text-muted-foreground border-border hover:bg-secondary hover:text-foreground"
                        }`}
                      >
                        {level}
                      </button>
                    );
                  })}
                </div>
                <p className="text-[11px] text-muted-foreground pt-1">
                  Used alongside skill match to tailor issue suggestions to your background.
                </p>
              </div>

              {/* Interests */}
              {renderSkillSection(
                "Interests & Learning Goals",
                "interests",
                QUICK_SUGGESTIONS.interests
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
