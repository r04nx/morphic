import { Link, useRouterState } from "@tanstack/react-router";
import { ChevronRight, Home } from "lucide-react";
import { cn } from "@/lib/utils";

interface BreadcrumbItem {
  label: string;
  href?: string;
  isCurrent?: boolean;
}

export function Breadcrumbs() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  
  const breadcrumbs = generateBreadcrumbs(pathname);
  
  if (breadcrumbs.length <= 1) {
    return null;
  }

  return (
    <nav className="flex items-center space-x-1 text-sm text-muted-foreground" aria-label="Breadcrumb">
      <ol className="flex items-center space-x-1">
        {breadcrumbs.map((item, index) => (
          <li key={index} className="flex items-center">
            {index > 0 && (
              <ChevronRight className="mx-2 h-4 w-4 flex-shrink-0 text-muted-foreground/50" />
            )}
            {item.href && !item.isCurrent ? (
              <Link
                to={item.href}
                className={cn(
                  "transition-colors hover:text-foreground",
                  index === 0 && "flex items-center"
                )}
              >
                {index === 0 && <Home className="mr-1 h-4 w-4" />}
                {item.label}
              </Link>
            ) : (
              <span
                className={cn(
                  "font-medium text-foreground",
                  index === 0 && "flex items-center"
                )}
                aria-current={item.isCurrent ? "page" : undefined}
              >
                {index === 0 && <Home className="mr-1 h-4 w-4" />}
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function generateBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean);
  const breadcrumbs: BreadcrumbItem[] = [];
  
  // Always start with Home
  breadcrumbs.push({
    label: "Home",
    href: "/",
  });

  if (segments.length === 0) {
    // Already at home
    breadcrumbs[0].isCurrent = true;
    return breadcrumbs;
  }

  // Build breadcrumb trail
  let currentPath = "";
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    currentPath += `/${segment}`;
    const isLast = i === segments.length - 1;
    
    // Handle dynamic routes
    let label = segment;
    let href = currentPath;
    
    if (segment === 'incidents') {
      label = "Incidents";
      if (!isLast) {
        href = "/incidents";
      }
    } else if (segment === 'monitors') {
      label = "Monitors";
      if (!isLast) {
        href = "/monitors";
      }
    } else if (segment === 'actions') {
      label = "Actions";
    } else if (segment === 'settings') {
      label = "Settings";
    } else if (segment === 'traces') {
      label = "Traces";
    } else if (/^[a-f0-9-]{36}$/i.test(segment)) {
      // UUID pattern for incident/monitor/trace IDs
      label = segment.substring(0, 8) + "...";
    } else if (/^[a-zA-Z0-9_-]+$/.test(segment)) {
      // Handle trace IDs or other identifiers
      if (segments[i-1] === 'traces') {
        label = `Trace: ${segment}`;
      } else if (segments[i-1] === 'incidents') {
        label = `Incident: ${segment}`;
      } else if (segments[i-1] === 'monitors') {
        label = `Monitor: ${segment}`;
      } else {
        label = segment;
      }
    }
    
    breadcrumbs.push({
      label,
      href: isLast ? undefined : href,
      isCurrent: isLast,
    });
  }

  return breadcrumbs;
}
