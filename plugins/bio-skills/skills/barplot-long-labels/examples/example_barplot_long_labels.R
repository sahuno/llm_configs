#!/usr/bin/env Rscript
#############################################
## Example: Barplot with Long Y-Axis Labels
## Author: Samuel Ahuno
## Date: 2026-01-29
##
## Purpose: Demonstrate the barplot-long-labels skill with simulated data
##
## Usage: Rscript example_barplot_long_labels.R
#############################################

library(ggplot2)
library(dplyr)
library(stringr)

# Source the dimension calculator
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/barplot-long-labels/calc_barplot_dimensions.R")

#############################################
## Create Simulated GO Enrichment Data
#############################################

go_pathway_names <- c(
  "regulation of cell death",
  "response to oxidative stress",
  "cell cycle arrest",
  "apoptotic process",
  "inflammatory response",
  "positive regulation of transcription by RNA polymerase II",
  "negative regulation of apoptotic signaling pathway",
  "cellular response to DNA damage stimulus",
  "regulation of mitochondrial membrane permeability",
  "activation of cysteine-type endopeptidase activity",
  "positive regulation of transcription from RNA polymerase II promoter in response to stress",
  "regulation of intrinsic apoptotic signaling pathway in response to DNA damage"
)

set.seed(42)
n_pathways <- 10

example_data <- data.frame(
  Description = sample(go_pathway_names, n_pathways, replace = FALSE),
  p.adjust = sort(runif(n_pathways, min = 1e-8, max = 0.05)),
  Direction = sample(c("Upregulated", "Downregulated"), n_pathways, replace = TRUE)
)

message("=== Example Data ===")
print(head(example_data))

#############################################
## Method 1: Manual Approach (Step by Step)
#############################################

message("\n=== Method 1: Manual Step-by-Step ===")

# Parameters
base_size <- 20
wrap_width <- 50
base_bar_width_mm <- 180

# Step 1: Prepare data
plot_data <- example_data %>%
  mutate(
    label_wrapped = str_wrap(Description, width = wrap_width)
  ) %>%
  arrange(desc(Direction), p.adjust) %>%
  mutate(
    label_wrapped = factor(label_wrapped, levels = rev(unique(label_wrapped)))
  )

# Step 2: Calculate dimensions
dims <- calc_barplot_dimensions(
  data = plot_data,
  y_col = "label_wrapped",
  base_bar_width_mm = base_bar_width_mm,
  base_size = base_size,
  wrap_width = wrap_width
)

# Step 3: Create plot
p_manual <- ggplot(plot_data, aes(x = -log10(p.adjust),
                                   y = label_wrapped,
                                   fill = Direction)) +
  geom_bar(stat = "identity", alpha = 0.85, width = 0.7) +
  scale_fill_manual(
    values = c("Upregulated" = "#D62728", "Downregulated" = "#1F77B4"),
    name = "Gene Regulation"
  ) +
  scale_x_continuous(
    name = expression(-Log[10]~"(Adjusted P-value)"),
    expand = expansion(mult = c(0, 0.05))
  ) +
  labs(
    title = "GO Biological Process Enrichment",
    subtitle = paste0("Method 1: Manual | ", dims$width_mm, "mm x ", dims$height_mm, "mm"),
    y = NULL
  ) +
  theme_bw(base_size = base_size) +
  theme(
    plot.title = element_text(face = "bold", size = base_size * 1.2, hjust = 0.5),
    plot.subtitle = element_text(size = base_size * 0.8, hjust = 0.5, color = "grey40"),
    axis.text.y = element_text(size = base_size * 0.8, color = "black"),
    axis.text.x = element_text(size = base_size * 0.7, color = "black"),
    axis.title.x = element_text(size = base_size, face = "bold"),
    legend.position = "top",
    legend.text = element_text(size = base_size * 0.7),
    legend.title = element_text(face = "bold", size = base_size * 0.8),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank()
  )

# Step 4: Save
output_dir <- "figures/example_barplot_long_labels"
dir.create(file.path(output_dir, "pdf"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "png"), recursive = TRUE, showWarnings = FALSE)

ggsave(p_manual,
       filename = file.path(output_dir, "pdf", "example_method1_manual.pdf"),
       width = dims$width_mm, height = dims$height_mm, units = "mm")
ggsave(p_manual,
       filename = file.path(output_dir, "png", "example_method1_manual.png"),
       width = dims$width_mm, height = dims$height_mm, units = "mm", dpi = 300)

message("Saved Method 1 plots to: ", output_dir)

#############################################
## Method 2: Using Convenience Functions
#############################################

message("\n=== Method 2: Using Convenience Functions ===")

# Use the convenience function
p_convenience <- create_barplot_long_labels(
  data = example_data,
  y_col = "Description",
  x_col = "p.adjust",
  fill_col = "Direction",
  title = "GO Biological Process Enrichment",
  subtitle = "Method 2: Convenience Function",
  x_label = "Adjusted P-value",
  base_size = 20,
  wrap_width = 50,
  fill_colors = c("Upregulated" = "#D62728", "Downregulated" = "#1F77B4")
)

# Calculate dimensions using the prepared data (after wrapping)
dims2 <- calc_barplot_dimensions(
  data = example_data,
  y_col = "Description",
  base_bar_width_mm = 180,
  base_size = 20,
  wrap_width = 50
)

# Save using the multi-format function
save_barplot_multiformat(
  plot = p_convenience,
  filename_base = "example_method2_convenience",
  output_dir = output_dir,
  dims = dims2,
  formats = c("pdf", "png")
)

#############################################
## Summary
#############################################

message("\n=== Summary ===")
message("Output directory: ", output_dir)
message("Files generated:")
message("  - example_method1_manual.pdf/png")
message("  - example_method2_convenience.pdf/png")
message("\nCalculated dimensions: ", dims$width_mm, "mm x ", dims$height_mm, "mm")
message("\nDone!")
