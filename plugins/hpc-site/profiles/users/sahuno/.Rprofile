# ~/.Rprofile

if (requireNamespace("showtext", quietly = TRUE)) {
  library(showtext)

  # Cross-platform Arial path detection
  arial_paths <- c(
    "/System/Library/Fonts/Supplemental/Arial.ttf",                      # macOS
    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",                # Linux (Debian/Ubuntu)
    "C:/Windows/Fonts/arial.ttf"                                        # Windows
  )
  arial_path <- arial_paths[file.exists(arial_paths)][1]

  if (!is.na(arial_path)) {
    font_add(family = "Arial", regular = arial_path)
    showtext_auto()
  } else {
    warning("Arial font not found on this system.")
  }
}

# Set ggplot2 default theme
if (requireNamespace("ggplot2", quietly = TRUE)) {
  library(ggplot2)
  theme_set(theme_minimal(base_family = "Arial", base_size = 12))
}

