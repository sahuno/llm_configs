#!/usr/bin/env Rscript
#############################################
## Example: Sample Correlation Heatmap
## Author: Samuel Ahuno
## Date: 2026-01-30
##
## Creates a publication-ready correlation heatmap
## showing sample-to-sample correlations
#############################################

# --- Load packages ------------------------------------------------------------
library(ComplexHeatmap)
library(RColorBrewer)
library(circlize)  # For color mapping

# --- Source dimension calculation functions -----------------------------------
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/heatmap-dimensions/calc_heatmap_dimensions.R")

# --- Simulate example data ----------------------------------------------------
set.seed(42)

n_samples <- 20
n_genes <- 1000

# Simulate expression data with group structure
groups <- rep(c("Group_A", "Group_B", "Group_C", "Group_D"), each = 5)
batches <- rep(c("Batch1", "Batch2"), 10)

expr_matrix <- matrix(rnorm(n_genes * n_samples), nrow = n_genes, ncol = n_samples)
colnames(expr_matrix) <- paste0("Sample_", 1:n_samples)
rownames(expr_matrix) <- paste0("Gene_", 1:n_genes)

# Add group effects
for (g in unique(groups)) {
  samples_in_group <- which(groups == g)
  group_effect <- rnorm(n_genes, mean = 0, sd = 1)
  expr_matrix[, samples_in_group] <- expr_matrix[, samples_in_group] + group_effect
}

# --- Calculate correlation matrix ---------------------------------------------
cor_matrix <- cor(expr_matrix, method = "pearson")

# --- Calculate dimensions -----------------------------------------------------
# For correlation heatmap: n_genes = n_samples (square matrix)
dims <- calc_heatmap_dimensions(
  n_genes = n_samples,
  n_samples = n_samples,
  n_annotation_tracks = 2  # Group + Batch
)

# For square correlation matrix, we might want to adjust
# Since it's symmetric, we can show all labels
dims$show_row_labels <- TRUE
dims$show_col_labels <- TRUE

# --- Prepare annotations ------------------------------------------------------
sample_metadata <- data.frame(
  Group = groups,
  Batch = batches,
  row.names = colnames(expr_matrix)
)

# --- Create heatmap -----------------------------------------------------------
library(grid)

# Define annotation colors
anno_colors <- list(
  Group = c(
    "Group_A" = "#0072B2",
    "Group_B" = "#E69F00",
    "Group_C" = "#009E73",
    "Group_D" = "#CC79A7"
  ),
  Batch = c(
    "Batch1" = "#56B4E9",
    "Batch2" = "#F0E442"
  )
)

# Column annotation
col_anno <- HeatmapAnnotation(
  df = sample_metadata,
  col = anno_colors,
  annotation_name_gp = gpar(fontsize = dims$fontsize_col)
)

# Row annotation (same as column for symmetric matrix)
row_anno <- rowAnnotation(
  df = sample_metadata,
  col = anno_colors,
  show_annotation_name = FALSE
)

# Color palette for correlation (diverging, centered at 0.5 or 1)
# Since correlation ranges from -1 to 1, but sample correlations are usually positive
cor_colors <- colorRamp2(
  c(min(cor_matrix), 0.7, 1),
  c("white", "orange", "red")
)

# Create heatmap
ht <- Heatmap(
  cor_matrix,
  name = "Correlation",
  col = cor_colors,

  # Title
  column_title = "Sample-to-Sample Correlation",
  column_title_gp = gpar(fontsize = dims$fontsize_title, fontface = "bold"),

  # Show names (symmetric matrix, show all)
  show_row_names = TRUE,
  show_column_names = TRUE,

  # Clustering
  cluster_rows = TRUE,
  cluster_columns = TRUE,

  # Font sizes
  row_names_gp = gpar(fontsize = dims$fontsize_row),
  column_names_gp = gpar(fontsize = dims$fontsize_col),

  # Dendrograms
  row_dend_width = unit(15, "mm"),
  column_dend_height = unit(15, "mm"),

  # Annotations
  top_annotation = col_anno,
  left_annotation = row_anno,

  # Legend
  heatmap_legend_param = list(
    title = "Pearson\nCorrelation",
    title_gp = gpar(fontsize = dims$fontsize_legend, fontface = "bold"),
    labels_gp = gpar(fontsize = dims$fontsize_legend)
  ),

  # Cell formatting (optional: show correlation values)
  # cell_fun = function(j, i, x, y, width, height, fill) {
  #   grid.text(sprintf("%.2f", cor_matrix[i, j]), x, y,
  #             gp = gpar(fontsize = 6))
  # }
)

# --- Save ---------------------------------------------------------------------
output_dir <- "figures"
save_heatmap(ht, "sample_correlation_heatmap", dims, output_dir)

message("\n=== Complete ===")
message("Correlation heatmap saved to: ", output_dir)
message("Dimensions: ", dims$width_mm, "mm x ", dims$height_mm, "mm")
