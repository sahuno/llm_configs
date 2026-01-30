#!/usr/bin/env Rscript
#############################################
## Calculate Barplot Dimensions for Long Y-Axis Labels
## Author: Samuel Ahuno
## Date: 2026-01-29
##
## Purpose: Compute optimal width and height for horizontal barplots
##          with categorical y-axis labels (e.g., GO pathway names)
##
## Part of: ggplot-barplot-long-labels skill
##
## Usage:
##   source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/barplot-long-labels/calc_barplot_dimensions.R")
##   dims <- calc_barplot_dimensions(data, y_col = "Description")
##   ggsave(plot, width = dims$width_mm, height = dims$height_mm, units = "mm")
#############################################

#' Calculate appropriate barplot width based on y-axis label length
#'
#' @param chars_longest_label Number of characters in longest y-axis label
#' @param base_bar_width_mm Target width for the bar area (default: 180mm)
#' @param base_size ggplot2 theme base font size in points (default: 20)
#' @param font_type "proportional" or "monospace" (default: "proportional")
#' @return Total plot width in mm (rounded to nearest 5mm)
#' @examples
#' calc_barplot_width(chars_longest_label = 50)
#' # Returns 335mm
calc_barplot_width <- function(chars_longest_label,
                                base_bar_width_mm = 180,
                                base_size = 20,
                                font_type = "proportional") {

  # Step 1: Axis text font size (80% of base_size in ggplot2 themes)
  axis_font_pt <- base_size * 0.8

  # Step 2: Convert points to mm (1 pt = 0.3528 mm)
  char_height_mm <- axis_font_pt * 0.3528

  # Step 3: Estimate character width based on font type
  # Proportional fonts (Arial, Helvetica): avg width ~ 0.45 x height
  # Monospace fonts (Courier): width ~ 0.6 x height
  width_factor <- ifelse(font_type == "monospace", 0.6, 0.45)
  char_width_mm <- char_height_mm * width_factor

  # Step 4: Calculate label area
  label_text_mm <- chars_longest_label * char_width_mm
  left_padding_mm <- 10  # axis line, ticks, small margin

  # Step 5: Total width
  right_margin_mm <- 15

  total_width_mm <- label_text_mm + left_padding_mm + base_bar_width_mm + right_margin_mm

  # Round up to nearest 5mm
  return(ceiling(total_width_mm / 5) * 5)
}


#' Calculate appropriate barplot height based on number of categories
#'
#' @param n_categories Number of categories (pathways) on y-axis
#' @param base_size ggplot2 theme base font size in points (default: 20)
#' @return Total plot height in mm (rounded to nearest 5mm)
#' @examples
#' calc_barplot_height(n_categories = 14)
#' # Returns 220mm
calc_barplot_height <- function(n_categories, base_size = 20) {
  # Space per category scales with font size
  # At base_size=20, this gives ~12mm per category
  space_per_category_mm <- base_size * 0.6

  # Fixed overhead for title, subtitle, legend, x-axis, margins
  fixed_overhead_mm <- 50

  height_mm <- fixed_overhead_mm + (n_categories * space_per_category_mm)
  return(ceiling(height_mm / 5) * 5)
}


#' Calculate both width and height for a barplot based on data
#'
#' This is the main function to use. It takes a data frame and the column
#' name containing y-axis labels, then computes optimal dimensions.
#'
#' @param data Data frame containing the plot data
#' @param y_col Column name (string) for y-axis labels (default: "Description")
#' @param base_bar_width_mm Target width for the bar area (default: 180mm)
#' @param base_size ggplot2 theme base font size in points (default: 20)
#' @param font_type "proportional" or "monospace" (default: "proportional")
#' @param wrap_width If provided, uses this as max chars instead of actual max
#'                   (useful when using str_wrap in plot). Default: NULL
#' @return Named list with width_mm and height_mm
#' @examples
#' # Basic usage
#' dims <- calc_barplot_dimensions(enrichment_data, y_col = "Description")
#' ggsave(p, width = dims$width_mm, height = dims$height_mm, units = "mm")
#'
#' # With text wrapping (use wrap_width to match str_wrap setting)
#' dims <- calc_barplot_dimensions(data, y_col = "pathway", wrap_width = 50)
calc_barplot_dimensions <- function(data,
                                     y_col = "Description",
                                     base_bar_width_mm = 180,
                                     base_size = 20,
                                     font_type = "proportional",
                                     wrap_width = NULL) {

  # Validate inputs
  if (!is.data.frame(data)) {
    stop("'data' must be a data frame")
  }

  if (!y_col %in% names(data)) {
    stop(paste0("Column '", y_col, "' not found in data. ",
                "Available columns: ", paste(names(data), collapse = ", ")))
  }

  # Get y-axis labels
  y_labels <- as.character(data[[y_col]])

  if (length(y_labels) == 0) {
    stop("No data in the specified column")
  }

  # Calculate number of categories
  n_categories <- length(unique(y_labels))

  # Calculate longest label length
  if (!is.null(wrap_width)) {
    # If using str_wrap, the effective max is the wrap width
    chars_longest_label <- wrap_width
  } else {
    chars_longest_label <- max(nchar(y_labels), na.rm = TRUE)
  }

  # Calculate dimensions
  width_mm <- calc_barplot_width(
    chars_longest_label = chars_longest_label,
    base_bar_width_mm = base_bar_width_mm,
    base_size = base_size,
    font_type = font_type
  )

  height_mm <- calc_barplot_height(
    n_categories = n_categories,
    base_size = base_size
  )

  # Return as named list

  result <- list(
    width_mm = width_mm,
    height_mm = height_mm,
    n_categories = n_categories,
    chars_longest_label = chars_longest_label,
    base_bar_width_mm = base_bar_width_mm,
    base_size = base_size
  )

  # Print summary message
  message("=== Barplot Dimensions ===")
  message("  Categories (y-axis): ", n_categories)
  message("  Longest label: ", chars_longest_label, " chars")
  message("  Base bar width: ", base_bar_width_mm, " mm")
  message("  Base size: ", base_size, " pt")
  message("  --> Width: ", width_mm, " mm")
  message("  --> Height: ", height_mm, " mm")

  return(result)
}


#' Print a quick reference table for common scenarios
#'
#' @param base_size ggplot2 theme base font size (default: 20)
#' @param base_bar_width_mm Target bar area width (default: 180mm)
#' @return Data frame with reference values (also prints to console)
#' @examples
#' print_dimension_reference_table()
print_dimension_reference_table <- function(base_size = 20, base_bar_width_mm = 180) {

  message("\n=== Width Reference (base_size=", base_size,
          ", bar_width=", base_bar_width_mm, "mm) ===")

  width_ref <- data.frame(
    max_label_chars = seq(20, 100, by = 10)
  )
  width_ref$width_mm <- sapply(width_ref$max_label_chars,
                                calc_barplot_width,
                                base_bar_width_mm = base_bar_width_mm,
                                base_size = base_size)
  print(width_ref)

  message("\n=== Height Reference (base_size=", base_size, ") ===")

  height_ref <- data.frame(
    n_categories = c(5, 10, 15, 20, 25, 30)
  )
  height_ref$height_mm <- sapply(height_ref$n_categories,
                                  calc_barplot_height,
                                  base_size = base_size)
  print(height_ref)

  invisible(list(width_ref = width_ref, height_ref = height_ref))
}


#' Create a complete barplot with long y-axis labels
#'
#' Convenience function that creates a publication-ready barplot
#'
#' @param data Data frame with plot data
#' @param y_col Column name for y-axis labels
#' @param x_col Column name for x-axis values (bar lengths)
#' @param fill_col Column name for fill grouping (optional)
#' @param title Plot title
#' @param subtitle Plot subtitle (optional)
#' @param x_label X-axis label
#' @param base_size Theme base font size (default: 20)
#' @param wrap_width Character width for label wrapping (default: 50)
#' @param fill_colors Named vector of fill colors (optional)
#' @return ggplot object
create_barplot_long_labels <- function(data,
                                        y_col,
                                        x_col,
                                        fill_col = NULL,
                                        title = "Barplot",
                                        subtitle = NULL,
                                        x_label = "Value",
                                        base_size = 20,
                                        wrap_width = 50,
                                        fill_colors = NULL) {

  # Check for required packages
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("ggplot2 package is required")
  }
  if (!requireNamespace("stringr", quietly = TRUE)) {
    stop("stringr package is required")
  }

  # Prepare data
  plot_data <- data
  plot_data$y_label_wrapped <- stringr::str_wrap(plot_data[[y_col]], width = wrap_width)
  plot_data$y_label_wrapped <- factor(plot_data$y_label_wrapped,
                                       levels = rev(unique(plot_data$y_label_wrapped)))

  # Build the plot
  if (!is.null(fill_col) && fill_col %in% names(plot_data)) {
    p <- ggplot2::ggplot(plot_data, ggplot2::aes(x = .data[[x_col]],
                                                   y = y_label_wrapped,
                                                   fill = .data[[fill_col]]))
  } else {
    p <- ggplot2::ggplot(plot_data, ggplot2::aes(x = .data[[x_col]],
                                                   y = y_label_wrapped))
  }

  p <- p +
    ggplot2::geom_bar(stat = "identity", alpha = 0.85, width = 0.7) +
    ggplot2::scale_x_continuous(
      name = x_label,
      expand = ggplot2::expansion(mult = c(0, 0.05))
    ) +
    ggplot2::labs(
      title = title,
      subtitle = subtitle,
      y = NULL
    ) +
    ggplot2::theme_bw(base_size = base_size) +
    ggplot2::theme(
      plot.title = ggplot2::element_text(face = "bold", size = base_size * 1.2, hjust = 0.5),
      plot.subtitle = ggplot2::element_text(size = base_size * 0.8, hjust = 0.5, color = "grey40"),
      axis.text.y = ggplot2::element_text(size = base_size * 0.8, color = "black"),
      axis.text.x = ggplot2::element_text(size = base_size * 0.7, color = "black"),
      axis.title.x = ggplot2::element_text(size = base_size, face = "bold"),
      legend.position = "top",
      legend.text = ggplot2::element_text(size = base_size * 0.7),
      legend.title = ggplot2::element_text(face = "bold", size = base_size * 0.8),
      panel.grid.major.y = ggplot2::element_blank(),
      panel.grid.minor = ggplot2::element_blank(),
      plot.margin = ggplot2::margin(t = 10, r = 10, b = 10, l = 10, unit = "pt")
    )

  # Add custom fill colors if provided
  if (!is.null(fill_colors) && !is.null(fill_col)) {
    p <- p + ggplot2::scale_fill_manual(values = fill_colors)
  }

  return(p)
}


#' Save barplot in multiple formats with calculated dimensions
#'
#' @param plot ggplot object
#' @param filename_base Base filename without extension
#' @param output_dir Base output directory
#' @param dims Dimension list from calc_barplot_dimensions()
#' @param formats Vector of formats to save (default: c("pdf", "png", "svg"))
#' @param dpi DPI for png output (default: 300)
#' @return Invisible list of saved file paths
save_barplot_multiformat <- function(plot,
                                      filename_base,
                                      output_dir = "figures/barplots",
                                      dims,
                                      formats = c("pdf", "png", "svg"),
                                      dpi = 300) {

  saved_files <- list()

  for (fmt in formats) {
    # Create format subdirectory
    fmt_dir <- file.path(output_dir, fmt)
    dir.create(fmt_dir, recursive = TRUE, showWarnings = FALSE)

    # Build filename
    filepath <- file.path(fmt_dir, paste0(filename_base, ".", fmt))

    # Save with appropriate settings
    if (fmt == "png") {
      ggplot2::ggsave(plot, filename = filepath,
                      width = dims$width_mm, height = dims$height_mm,
                      units = "mm", dpi = dpi)
    } else {
      ggplot2::ggsave(plot, filename = filepath,
                      width = dims$width_mm, height = dims$height_mm,
                      units = "mm")
    }

    saved_files[[fmt]] <- filepath
    message("Saved: ", filepath)
  }

  invisible(saved_files)
}
