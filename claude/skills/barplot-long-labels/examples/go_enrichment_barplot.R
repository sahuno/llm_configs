#!/usr/bin/env Rscript
#############################################
## GO Enrichment Barplot with Long Y-Axis Labels
## Author: Samuel Ahuno
## Date: 2026-01-29
##
## Complete example showing how to create publication-quality
## horizontal barplots with automatically calculated dimensions
#############################################

library(ggplot2)
library(dplyr)
library(stringr)

# Source the dimension calculator
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/barplot-long-labels/calc_barplot_dimensions.R")

#############################################
## Parameters
#############################################

base_size <- 20
wrap_width <- 50
base_bar_width_mm <- 180
top_n <- 10

#############################################
## Prepare Data
#############################################

# Assuming 'enrichment_results' is your data frame with columns:
# - Description: pathway names
# - p.adjust: adjusted p-values
# - Direction: "Upregulated" or "Downregulated"

plot_data <- enrichment_results %>%
  slice_min(p.adjust, n = top_n) %>%
  mutate(
    # Wrap long labels
    label_wrapped = str_wrap(Description, width = wrap_width),
    # Create factor with correct order
    label_wrapped = factor(label_wrapped, levels = rev(unique(label_wrapped)))
  ) %>%
  arrange(desc(Direction), p.adjust)

#############################################
## Calculate Dimensions
#############################################

dims <- calc_barplot_dimensions(
  data = plot_data,
  y_col = "label_wrapped",
  base_bar_width_mm = base_bar_width_mm,
  base_size = base_size,
  wrap_width = wrap_width
)

#############################################
## Create Plot
#############################################

p <- ggplot(plot_data, aes(x = -log10(p.adjust),
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
    subtitle = "Top pathways by adjusted p-value",
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
    panel.grid.minor = element_blank(),
    plot.margin = margin(t = 10, r = 10, b = 10, l = 10, unit = "pt")
  )

#############################################
## Save with Calculated Dimensions
#############################################

output_base <- "figures/enrichment"
for (fmt in c("pdf", "png", "svg")) {
  dir.create(file.path(output_base, fmt), recursive = TRUE, showWarnings = FALSE)
}

filename_base <- "GO_BP_enrichment_barplot"

ggsave(p, filename = file.path(output_base, "pdf", paste0(filename_base, ".pdf")),
       width = dims$width_mm, height = dims$height_mm, units = "mm")

ggsave(p, filename = file.path(output_base, "png", paste0(filename_base, ".png")),
       width = dims$width_mm, height = dims$height_mm, units = "mm", dpi = 300)

ggsave(p, filename = file.path(output_base, "svg", paste0(filename_base, ".svg")),
       width = dims$width_mm, height = dims$height_mm, units = "mm")

message("Saved: ", filename_base, " at ", dims$width_mm, "mm x ", dims$height_mm, "mm")
