# Module File Templates

## Table of Contents
- [Type A — Standard bioconda](#type-a)
- [Type B — Licensed / non-bioconda](#type-b)
- [Type C — GPU required](#type-c)
- [Type D — R/Python script template](#type-d)
- [Shared: meta.yml skeleton](#metayml)
- [Shared: tests/main.nf.test skeleton](#nftest)

---

## Type A — Standard bioconda {#type-a}

### main.nf
```groovy
process TOOL_SUBTOOL {
    tag "$meta.id"
    label 'process_medium'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/TOOL:VERSION--HASH' :
        'quay.io/biocontainers/TOOL:VERSION--HASH' }"

    input:
    tuple val(meta), path(input)

    output:
    tuple val(meta), path("*.OUTPUT_EXT"), emit: output
    path "versions.yml"                  , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args   = task.ext.args   ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    TOOL \\
        SUBTOOL \\
        ${args} \\
        ${input} \\
        > ${prefix}.OUTPUT_EXT

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        TOOL: \$(TOOL --version 2>&1 | sed 's/TOOL version //')
    END_VERSIONS
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.OUTPUT_EXT

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        TOOL: 0.0.0
    END_VERSIONS
    """
}
```

### environment.yml
```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/nf-core/modules/master/modules/environment-schema.json
channels:
  - conda-forge
  - bioconda
dependencies:
  - bioconda::TOOL=VERSION
```

---

## Type B — Licensed / non-bioconda {#type-b}

### main.nf
```groovy
process TOOL_SUBTOOL {
    tag "$meta.id"
    label 'process_medium'

    // TOOL is not on bioconda (LICENCE_NAME licence).
    // Using official Docker Hub image directly —
    // same pattern as nf-core/parabricks modules (nvcr.io/nvidia/...).
    // Tracking semver Docker tags: UPSTREAM_ISSUE_URL
    conda null
    container "ORG/TOOL:VERSION_OR_SHA"

    input:
    tuple val(meta), path(input)

    output:
    tuple val(meta), path("*.OUTPUT_EXT")  , emit: output
    tuple val("${task.process}"), val('TOOL'), eval("TOOL --version 2>&1 | head -1"), emit: versions_tool, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args   = task.ext.args   ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    TOOL \\
        SUBTOOL \\
        ${args} \\
        ${input} \\
        > ${prefix}.OUTPUT_EXT
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.OUTPUT_EXT

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        TOOL: VERSION
    END_VERSIONS
    """
}
```

### environment.yml
```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/nf-core/modules/master/modules/environment-schema.json
# NOTE: TOOL is not available on bioconda (LICENCE_NAME licence).
# This environment.yml is a placeholder. The module uses the Docker/Singularity
# container specified in main.nf.
# Track TODO: submit TOOL to bioconda once licence permits.
channels:
  - conda-forge
  - bioconda
dependencies: []
```

### tests/nextflow.config
```groovy
process {
    withName: 'TOOL_SUBTOOL' {
        ext.args = params.module_args ?: ''
    }
}

// Prevent quay.io/ prefix — ORG/TOOL is on Docker Hub, not quay.io
singularity.registry = ''
docker.registry      = ''
```

---

## Type C — GPU required {#type-c}

### main.nf
```groovy
process TOOL_SUBTOOL {
    tag "$meta.id"
    label 'process_gpu'

    // TOOL is not on bioconda (LICENCE_NAME licence). GPU required.
    // Using official Docker Hub image — same pattern as nf-core/parabricks.
    // Tracking semver tags: UPSTREAM_ISSUE_URL
    conda null
    container "ORG/TOOL:VERSION_OR_SHA"

    input:
    tuple val(meta), path(input)

    output:
    tuple val(meta), path("*.OUTPUT_EXT")  , emit: output
    tuple val("${task.process}"), val('TOOL'), eval("TOOL --version 2>&1 | head -1"), emit: versions_tool, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args   = task.ext.args   ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    // Note: --device is hardcoded; override via ext.args (e.g. --device cpu) if needed
    """
    TOOL \\
        SUBTOOL \\
        ${args} \\
        --device cuda:all \\
        ${input} \\
        > ${prefix}.OUTPUT_EXT
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.OUTPUT_EXT

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        TOOL: VERSION
    END_VERSIONS
    """
}
```

### tests/nextflow.config
```groovy
process {
    withName: 'TOOL_SUBTOOL' {
        ext.args = params.module_args ?: ''
    }
}

// Prevent quay.io/ prefix — ORG/TOOL is on Docker Hub, not quay.io
singularity.registry = ''
docker.registry      = ''

// Expose GPU to Singularity container (required for CUDA access)
singularity.runOptions = '--nv'
```

### tests/main.nf.test — GPU test block
```groovy
// Real GPU tests — excluded from CI, run locally with --profile singularity,gpu --tag gpu
test("DESCRIPTION - real gpu") {

    tag "gpu"

    when {
        params {
            module_args = ''
        }
        process {
            """
            input[0] = [
                [ id: 'test' ],
                file("${projectDir}/modules/nf-core/TOOL/SUBTOOL/tests/data/test.INPUT_EXT", checkIfExists: true)
            ]
            """
        }
    }

    then {
        assertAll(
            { assert process.success },
            { assert snapshot(process.out).match() }
        )
    }
}
```

---

## Type D — R/Python script template {#type-d}

### main.nf
```groovy
process TOOL_SUBTOOL {
    tag "$meta.id"
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://WAVE_URI' :
        'WAVE_URI' }"

    input:
    tuple val(meta), path(inputs)
    tuple val(meta2), path(samplesheet)

    output:
    tuple val(meta), path("figures/png/*.png"), emit: png, optional: true
    tuple val(meta), path("figures/pdf/*.pdf"), emit: pdf, optional: true
    tuple val(meta), path("figures/svg/*.svg"), emit: svg, optional: true
    tuple val(meta), path("*_combined.tsv")   , emit: combined_tsv, optional: true
    path "versions.yml"                       , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    template 'script.R'

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    mkdir -p figures/png figures/pdf figures/svg
    touch figures/png/${prefix}_output.png
    touch figures/pdf/${prefix}_output.pdf
    touch figures/svg/${prefix}_output.svg
    touch ${prefix}_combined.tsv

    r_version=\$(Rscript -e "cat(as.character(getRversion()))" 2>/dev/null || echo "4.0.0")
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        r-base: \${r_version}
    END_VERSIONS
    """
}
```

### environment.yml (Type D)
```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/nf-core/modules/master/modules/environment-schema.json
channels:
  - conda-forge
  - bioconda
dependencies:
  - conda-forge::r-base=VERSION
  - conda-forge::r-ggplot2=VERSION
  - conda-forge::r-data.table=VERSION
```

Build Wave container:
```bash
wave -f <path-to-environment.yml-dir> --tower-token $TOWER_ACCESS_TOKEN
```
Use the returned URI in `main.nf`.

---

## Shared: meta.yml skeleton {#metayml}

```yaml
name: tool_subtool
description: |
  ONE SENTENCE DESCRIPTION.
keywords:
  - keyword1
  - keyword2
tools:
  - "TOOL":
      description: TOOL DESCRIPTION.
      homepage: https://github.com/ORG/TOOL
      documentation: https://docs.TOOL.org
      tool_dev_url: https://github.com/ORG/TOOL
      licence:
        - "LICENCE NAME"
      identifier: ""
input:
  - - meta:
        type: map
        description: |
          Groovy Map containing sample information
          e.g. `[ id:'test' ]`
    - input:
        type: file
        description: INPUT DESCRIPTION.
        pattern: "*.INPUT_EXT"
        ontologies: []
output:
  output:
    - - meta:
          type: map
          description: |
            Groovy Map containing sample information
            e.g. `[ id:'test' ]`
      - "*.OUTPUT_EXT":
          type: file
          description: OUTPUT DESCRIPTION.
          pattern: "*.OUTPUT_EXT"
          ontologies: []
  versions:
    - "versions.yml":
        type: file
        description: File containing software versions.
        pattern: "versions.yml"
authors:
  - "@sahuno"
maintainers:
  - "@sahuno"
```

---

## Shared: tests/main.nf.test skeleton {#nftest}

```groovy
nextflow_process {

    name "Test Process TOOL_SUBTOOL"
    script "../main.nf"
    process "TOOL_SUBTOOL"

    tag "modules"
    tag "modules_nfcore"
    tag "TOOL"
    tag "TOOL/SUBTOOL"

    test("SPECIES - INPUT_DESCRIPTION - stub") {

        options "-stub"

        when {
            params {
                module_args = ''
            }
            process {
                """
                input[0] = [
                    [ id: 'test' ],
                    file("${projectDir}/modules/nf-core/TOOL/SUBTOOL/tests/data/test.INPUT_EXT", checkIfExists: true)
                ]
                """
            }
        }

        then {
            assertAll(
                { assert process.success },
                { assert snapshot(process.out).match() }
            )
        }
    }
}
```
