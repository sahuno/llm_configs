#!/usr/bin/env Rscript
#############################################
## Calculate Heatmap Dimensions for Publication
## Author: Samuel Ahuno
## Date: 2026-01-30
##
## Purpose: Compute optimal width and height for heatmaps
##          based on number of genes (rows) and samples (columns)
##          following Nature journal specifications
##
## Part of: heatmap-dimensions skill
##
## Usage:
##   source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/heatmap-dimensions/calc_heatmap_dimensions.R")
##   dims <- calc_heatmap_dimensions(n_genes = 30, n_samples = 8)
##   save_heatmap(ht, "my_heatmap", dims)
#############################################

# --- Fixed Parameters (Nature Journal Specs) ---------------------------------
HEATMAP_WIDTH_MM <- 180
HEATMAP_BASE_SIZE <- 20
HEATMAP_MAX_HEIGHT_MM <- 170

# --- Thresholds for label visibility -----------------------------------------
MAX_GENES_WITH_LABELS <- 31
MAX_GENES_WITHOUT_LABELS <- 62
MAX_SAMPLES_WITH_LABELS <- 50

# --- Cell dimensions ---------------------------------------------------------
CELL_HEIGHT_WITH_LABELS_MM <- 4
CELL_HEIGHT_NO_LABELS_MM <- 2

# --- Overhead components (mm) ------------------------------------------------
OVERHEAD_COL_DENDROGRAM <- 15
OVERHEAD_ANNOTATION_PER_TRACK <- 8
OVERHEAD_TITLE <- 10
OVERHEAD_COL_LABELS <- 5
OVERHEAD_MARGINS <- 7


#' Calculate heatmap height based on number of genes
#'
#' @param n_genes Number of genes (rows)
#' @param show_row_labels Whether row labels will be shown
#' @param n_annotation_tracks Number of column annotation bars (default: 1)
#' @return Height in mm (capped at 170mm)
#' @examples
#' calc_heatmap_height(30, show_row_labels = TRUE)
#' # Returns 165
calc_heatmap_height <- function(n_genes,
                                 show_row_labels = NULL,
                                 n_annotation_tracks = 1) {

  # Auto-determine label visibility if not specified
  if (is.null(show_row_labels)) {
    show_row_labels <- n_genes <= MAX_GENES_WITH_LABELS
  }

  # Cell height depends on label visibility
  cell_height_mm <- ifelse(show_row_labels,
                           CELL_HEIGHT_WITH_LABELS_MM,
                           CELL_HEIGHT_NO_LABELS_MM)

  # Heatmap body height
  heatmap_body_mm <- n_genes * cell_height_mm

  # Overhead
  overhead_mm <- OVERHEAD_COL_DENDROGRAM +
                 (n_annotation_tracks * OVERHEAD_ANNOTATION_PER_TRACK) +
                 OVERHEAD_TITLE +
                 OVERHEAD_COL_LABELS +
                 OVERHEAD_MARGINS

  # Total height
  total_height_mm <- heatmap_body_mm + overhead_mm

  # Cap at max
  height_mm <- min(total_height_mm, HEATMAP_MAX_HEIGHT_MM)

  return(round(height_mm))
}


#' Calculate complete heatmap dimensions
#'
#' Main function to determine optimal heatmap dimensions based on data.
#' Returns width (fixed 180mm), calculated height, and label visibility flags.
#'
#' @param n_genes Number of genes (rows)
#' @param n_samples Number of samples (columns)
#' @param n_annotation_tracks Number of column annotation bars (default: 1)
#' @return Named list with dimensions and settings
#' @examples
#' dims <- calc_heatmap_dimensions(n_genes = 30, n_samples = 8)
#' # dims$width_mm = 180
#' # dims$height_mm = 165
#' # dims$show_row_labels = TRUE
calc_heatmap_dimensions <- function(n_genes,
                                     n_samples,
                                     n_annotation_tracks = 1) {

  # Determine label visibility
  show_row_labels <- n_genes <= MAX_GENES_WITH_LABELS
  show_col_labels <- n_samples <= MAX_SAMPLES_WITH_LABELS

  # Calculate height
  height_mm <- calc_heatmap_height(
    n_genes = n_genes,
    show_row_labels = show_row_labels,
    n_annotation_tracks = n_annotation_tracks
  )

  # Check if height was capped
  cell_height_mm <- ifelse(show_row_labels,
                           CELL_HEIGHT_WITH_LABELS_MM,
                           CELL_HEIGHT_NO_LABELS_MM)
  heatmap_body_mm <- n_genes * cell_height_mm
  overhead_mm <- OVERHEAD_COL_DENDROGRAM +
                 (n_annotation_tracks * OVERHEAD_ANNOTATION_PER_TRACK) +
                 OVERHEAD_TITLE + OVERHEAD_COL_LABELS + OVERHEAD_MARGINS
  uncapped_height <- heatmap_body_mm + overhead_mm
  is_capped <- uncapped_height > HEATMAP_MAX_HEIGHT_MM

  # Build result

  result <- list(
    # Dimensions
    width_mm = HEATMAP_WIDTH_MM,
    height_mm = height_mm,

    # Label visibility
    show_row_labels = show_row_labels,
    show_col_labels = show_col_labels,

    # Input parameters
    n_genes = n_genes,
    n_samples = n_samples,
    n_annotation_tracks = n_annotation_tracks,

    # Calculation details
    cell_height_mm = cell_height_mm,
    heatmap_body_mm = heatmap_body_mm,
    overhead_mm = overhead_mm,
    uncapped_height_mm = round(uncapped_height),
    is_capped = is_capped,

    # Font sizes (for ComplexHeatmap)
    fontsize_row = HEATMAP_BASE_SIZE * 0.4,   # 8pt
    fontsize_col = HEATMAP_BASE_SIZE * 0.5,   # 10pt
    fontsize_title = HEATMAP_BASE_SIZE * 0.6, # 12pt
    fontsize_legend = HEATMAP_BASE_SIZE * 0.5 # 10pt
  )

  # Print summary
  message("=== Heatmap Dimensions ===")
  message("  Genes (rows): ", n_genes)
  message("  Samples (cols): ", n_samples)
  message("  Annotation tracks: ", n_annotation_tracks)
  message("  Row labels: ", ifelse(show_row_labels, "SHOWN", "HIDDEN"))
  message("  Col labels: ", ifelse(show_col_labels, "SHOWN", "HIDDEN"))
  message("  --> Width: ", HEATMAP_WIDTH_MM, " mm (fixed)")
  message("  --> Height: ", height_mm, " mm",
          ifelse(is_capped, paste0(" (capped from ", round(uncapped_height), "mm)"), ""))

  return(result)
}


#' Print dimension reference table for common scenarios
#'
#' @return Data frame with reference values (also prints to console)
print_heatmap_dimension_table <- function() {

  message("\n=== Heatmap Height Reference (width=180mm, base_size=20) ===\n")

  # Create reference table
  ref_data <- data.frame(
    n_genes = c(10, 20, 30, 31, 40, 50, 60, 62, 75, 100, 150, 200),
    stringsAsFactors = FALSE
  )

  ref_data$show_labels <- ref_data$n_genes <= MAX_GENES_WITH_LABELS
  ref_data$cell_height <- ifelse(ref_data$show_labels,
                                  CELL_HEIGHT_WITH_LABELS_MM,
                                  CELL_HEIGHT_NO_LABELS_MM)
  ref_data$body_height <- ref_data$n_genes * ref_data$cell_height
  ref_data$overhead <- 45  # Approximate fixed overhead
  ref_data$uncapped <- ref_data$body_height + ref_data$overhead
  ref_data$height_mm <- pmin(ref_data$uncapped, HEATMAP_MAX_HEIGHT_MM)
  ref_data$status <- ifelse(ref_data$uncapped > HEATMAP_MAX_HEIGHT_MM,
                            "CAPPED", "OK")

  # Format for display
  display_df <- data.frame(
    n_genes = ref_data$n_genes,
    labels = ifelse(ref_data$show_labels, "yes", "no"),
    height_mm = paste0(ref_data$height_mm, "mm"),
    status = ref_data$status
  )

  print(display_df, row.names = FALSE)

  message("\nThresholds:")
  message("  - Show row labels: n_genes <= ", MAX_GENES_WITH_LABELS)
  message("  - Max height: ", HEATMAP_MAX_HEIGHT_MM, "mm")
  message("  - Cell height with labels: ", CELL_HEIGHT_WITH_LABELS_MM, "mm")
  message("  - Cell height without labels: ", CELL_HEIGHT_NO_LABELS_MM, "mm")

  invisible(ref_data)
}


#' Get colorblind-safe palette
#'
#' @param type "discrete" for annotation colors, "continuous" for heatmap body
#' @param n Number of colors needed (for discrete)
#' @return Vector of colors
get_colorblind_palette <- function(type = "discrete", n = 8) {

  # Okabe-Ito palette (colorblind-safe)
  okabe_ito <- c(
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#999999"   # grey
  )

  if (type == "discrete") {
    if (n > length(okabe_ito)) {
      warning("Requested ", n, " colors but only ", length(okabe_ito), " available. Colors will be recycled.")
    }
    return(okabe_ito[1:min(n, length(okabe_ito))])
  } else if (type == "continuous") {
    # Return viridis palette function
    if (!requireNamespace("viridis", quietly = TRUE)) {
      stop("viridis package required for continuous palette")
    }
    return(viridis::viridis(100))
  }
}


#' Create publication-ready heatmap with ComplexHeatmap
#'
#' @param matrix Numeric matrix (genes × samples), typically scaled
#' @param dims Dimension list from calc_heatmap_dimensions()
#' @param column_annotation Data frame with sample annotations (optional)
#' @param row_annotation Data frame with gene annotations (optional)
#' @param title Heatmap title
#' @param name Legend title (default: "Z-score")
#' @param cluster_rows Cluster rows? (default: TRUE)
#' @param cluster_columns Cluster columns? (default: TRUE)
#' @param color_palette Color palette for heatmap body
#' @param annotation_colors Named list of colors for annotations
#' @return ComplexHeatmap Heatmap object
create_publication_heatmap <- function(matrix,
                                        dims,
                                        column_annotation = NULL,
                                        row_annotation = NULL,
                                        title = "",
                                        name = "Z-score",
                                        cluster_rows = TRUE,
                                        cluster_columns = TRUE,
                                        color_palette = NULL,
                                        annotation_colors = NULL) {

  # Check for ComplexHeatmap
  if (!requireNamespace("ComplexHeatmap", quietly = TRUE)) {
    stop("ComplexHeatmap package is required. Install with: BiocManager::install('ComplexHeatmap')")
  }
  library(ComplexHeatmap)
  library(grid)

  # Default color palette
  if (is.null(color_palette)) {
    if (requireNamespace("viridis", quietly = TRUE)) {
      color_palette <- viridis::viridis(100)
    } else {
      color_palette <- colorRampPalette(c("navy", "white", "firebrick3"))(100)
    }
  }

  # Build column annotation if provided
  top_anno <- NULL
  if (!is.null(column_annotation)) {
    anno_cols <- list()

    # Generate colors for each annotation column
    for (col_name in names(column_annotation)) {
      values <- unique(column_annotation[[col_name]])
      if (is.null(annotation_colors) || !col_name %in% names(annotation_colors)) {
        # Auto-assign colorblind-safe colors
        anno_cols[[col_name]] <- setNames(
          get_colorblind_palette("discrete", length(values)),
          values
        )
      } else {
        anno_cols[[col_name]] <- annotation_colors[[col_name]]
      }
    }

    top_anno <- HeatmapAnnotation(
      df = column_annotation,
      col = anno_cols,
      annotation_name_gp = gpar(fontsize = dims$fontsize_col),
      annotation_legend_param = list(
        title_gp = gpar(fontsize = dims$fontsize_legend, fontface = "bold"),
        labels_gp = gpar(fontsize = dims$fontsize_legend)
      )
    )
  }

  # Build row annotation if provided
  left_anno <- NULL
  if (!is.null(row_annotation)) {
    anno_cols_row <- list()

    for (col_name in names(row_annotation)) {
      values <- unique(row_annotation[[col_name]])
      if (is.null(annotation_colors) || !col_name %in% names(annotation_colors)) {
        anno_cols_row[[col_name]] <- setNames(
          get_colorblind_palette("discrete", length(values)),
          values
        )
      } else {
        anno_cols_row[[col_name]] <- annotation_colors[[col_name]]
      }
    }

    left_anno <- rowAnnotation(
      df = row_annotation,
      col = anno_cols_row,
      annotation_name_gp = gpar(fontsize = dims$fontsize_row)
    )
  }

  # Create heatmap
  ht <- Heatmap(
    matrix,
    name = name,
    col = color_palette,

    # Title
    column_title = title,
    column_title_gp = gpar(fontsize = dims$fontsize_title, fontface = "bold"),

    # Row/column display
    show_row_names = dims$show_row_labels,
    show_column_names = dims$show_col_labels,

    # Clustering
    cluster_rows = cluster_rows,
    cluster_columns = cluster_columns,

    # Font sizes
    row_names_gp = gpar(fontsize = dims$fontsize_row),
    column_names_gp = gpar(fontsize = dims$fontsize_col),

    # Dendrograms
    row_dend_width = unit(15, "mm"),
    column_dend_height = unit(15, "mm"),

    # Annotations
    top_annotation = top_anno,
    left_annotation = left_anno,

    # Legend
    heatmap_legend_param = list(
      title_gp = gpar(fontsize = dims$fontsize_legend, fontface = "bold"),
      labels_gp = gpar(fontsize = dims$fontsize_legend),
      legend_height = unit(40, "mm")
    )
  )

  return(ht)
}


#' Save heatmap in multiple formats
#'
#' @param ht ComplexHeatmap object
#' @param filename_base Base filename without extension
#' @param dims Dimension list from calc_heatmap_dimensions()
#' @param output_dir Base output directory (default: "figures")
#' @param formats Vector of formats to save (default: c("pdf", "png", "svg"))
#' @param dpi DPI for PNG (default: 300)
#' @return Invisible list of saved file paths
save_heatmap <- function(ht,
                          filename_base,
                          dims,
                          output_dir = "figures",
                          formats = c("pdf", "png", "svg"),
                          dpi = 300) {

  if (!requireNamespace("ComplexHeatmap", quietly = TRUE)) {
    stop("ComplexHeatmap package is required")
  }

  # Convert mm to inches
  width_in <- dims$width_mm / 25.4
  height_in <- dims$height_mm / 25.4

  saved_files <- list()

  for (fmt in formats) {
    # Create format subdirectory
    fmt_dir <- file.path(output_dir, fmt)
    dir.create(fmt_dir, recursive = TRUE, showWarnings = FALSE)

    filepath <- file.path(fmt_dir, paste0(filename_base, ".", fmt))

    if (fmt == "pdf") {
      grDevices::cairo_pdf(filepath, width = width_in, height = height_in)
      ComplexHeatmap::draw(ht)
      grDevices::dev.off()
    } else if (fmt == "png") {
      grDevices::png(filepath, width = width_in, height = height_in,
                     units = "in", res = dpi)
      ComplexHeatmap::draw(ht)
      grDevices::dev.off()
    } else if (fmt == "svg") {
      grDevices::svg(filepath, width = width_in, height = height_in)
      ComplexHeatmap::draw(ht)
      grDevices::dev.off()
    }

    saved_files[[fmt]] <- filepath
    message("Saved: ", filepath)
  }

  invisible(saved_files)
}


#' Scale matrix by row (z-score normalization)
#'
#' Convenience function to scale expression matrix
#'
#' @param matrix Numeric matrix (genes × samples)
#' @return Scaled matrix (z-scores by row)
scale_matrix_by_row <- function(matrix) {
  scaled <- t(scale(t(matrix)))
  # Handle rows with zero variance
  scaled[is.nan(scaled)] <- 0
  return(scaled)
}
