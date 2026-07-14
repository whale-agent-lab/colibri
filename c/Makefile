UNAME_S := $(shell uname -s)
MINGW    := $(findstring MINGW,$(UNAME_S))
MSYS     := $(findstring MSYS,$(UNAME_S))
IS_WIN   := $(MINGW)$(MSYS)

ifeq ($(UNAME_S),Darwin)
# --- macOS / Apple Silicon ---
# Apple clang non include il runtime OpenMP: se c'e' libomp di Homebrew lo usa
# (brew install libomp), altrimenti compila single-thread (i pragma omp sono ignorati).
# Niente -march: su arm64 NEON e' baseline (i kernel __ARM_NEON si attivano da soli).
CC      = clang
OMPDIR := $(shell brew --prefix libomp 2>/dev/null)
ifneq ($(OMPDIR),)
OMPC    = -Xclang -fopenmp -I$(OMPDIR)/include
OMPL    = -L$(OMPDIR)/lib -lomp
else
$(warning libomp not found: building single-threaded. For multithreading: brew install libomp)
OMPC    =
OMPL    =
endif
CFLAGS  = -O3 $(OMPC) -Wall -Wextra -Wno-unused-parameter -Wno-misleading-indentation -Wno-unused-function
LDFLAGS = -lm $(OMPL)
EXE     =
else ifneq ($(IS_WIN),)
# --- Windows 11 x86-64 (MinGW-w64 / MSYS2) ---
# GCC + libgomp + winpthreads: pthread, OpenMP, clock_gettime, opendir/readdir,
# AVX2 intrinsics — tutto gratis, nessun porting.
# ARCH default = x86-64-v3 (binario portabile con AVX2). Per max velocita'
# su QUESTA macchina: make ARCH=native
CC      = gcc
ARCH   ?= x86-64-v3
CFLAGS  = -D_FILE_OFFSET_BITS=64 -O3 -march=$(ARCH) -fopenmp -Wall -Wextra -Wno-unused-parameter -Wno-misleading-indentation -Wno-unused-function
LDFLAGS = -lm -fopenmp -static
EXE     = .exe
else
UNAME_M := $(shell uname -m)
ifneq (,$(filter ppc64le ppc64,$(UNAME_M)))
# --- Linux PowerPC (POWER8/POWER9/POWER10) ---
# PowerPC GCC uses -mcpu, not -march. ARCH=native works on gcc >= 4.7.
# The AVX2/NEON kernels fall back to the portable scalar C path
# (validated token-exact vs the transformers oracle on a POWER8 S824).
CC      = gcc
ARCH   ?= native
CFLAGS  = -O3 -mcpu=$(ARCH) -fopenmp -Wall -Wextra -Wno-unused-parameter -Wno-misleading-indentation -Wno-unused-function
LDFLAGS = -lm -fopenmp
EXE     =
else
# --- Linux x86-64 (percorso originale, invariato) ---
CC      = gcc
# ARCH=native -> ottimizzato per QUESTA macchina (default, piu' veloce).
# ARCH=x86-64-v3 -> binario PORTABILE su qualsiasi x86-64 moderno con AVX2 (per distribuire).
# ARCH=x86-64 -> massima compatibilita' (niente AVX2: usa il path scalare di fallback).
ARCH   ?= native
CFLAGS  = -O3 -march=$(ARCH) -fopenmp -Wall -Wextra -Wno-unused-parameter -Wno-misleading-indentation -Wno-unused-function
LDFLAGS = -lm -fopenmp
EXE     =
endif
endif

# CUDA=1 adds an opt-in backend for resident tensors. The default build remains
# pure C and keeps the original zero-dependency runtime.
CUDA      ?= 0
CUDA_HOME ?= /usr/local/cuda
NVCC      ?= $(CUDA_HOME)/bin/nvcc
CUDA_ARCH ?= native
NVCCFLAGS ?= -O3 -std=c++17 -arch=$(CUDA_ARCH) -Xcompiler=-Wall,-Wextra
PYTHON    ?= python3
CUDA_OBJ  =
V4_TEST_BINS = tests/test_model_interfaces$(EXE) \
	tests/test_safetensors_index$(EXE) tests/test_native_quant$(EXE) \
	tests/test_deepseek_v4_expert_store$(EXE) \
	tests/test_deepseek_v4_math$(EXE) tests/test_deepseek_v4_expert$(EXE) \
	tests/test_deepseek_v4_config$(EXE) tests/test_tensor_io$(EXE) \
	tests/test_deepseek_v4_layer$(EXE) \
	tests/test_deepseek_v4_sparse_attention$(EXE) \
	tests/test_deepseek_v4_kv_cache$(EXE) \
	tests/test_deepseek_v4_attention_cache$(EXE) \
	tests/test_deepseek_v4_resource_plan$(EXE) \
	tests/test_deepseek_v4_prompt$(EXE)
V4_TOOL_BINS = tools/probe_deepseek_v4_layers$(EXE) \
	tools/probe_deepseek_v4_attention$(EXE) \
	tools/probe_deepseek_v4_block$(EXE) \
	tools/probe_deepseek_v4_compressor$(EXE) \
	tools/probe_deepseek_v4_ratio4_compressor$(EXE) \
	tools/probe_deepseek_v4_indexer$(EXE) \
	tools/probe_deepseek_v4_attention_sequence$(EXE) \
	tools/deepseek_v4_first_token$(EXE) \
	tools/deepseek_v4_tokenizer$(EXE)
TEST_BINS = tests/test_json$(EXE) tests/test_st$(EXE) tests/test_tier$(EXE) \
	tests/test_grammar$(EXE) tests/test_decode_batch$(EXE) \
	tests/test_idot$(EXE) $(V4_TEST_BINS)
ifeq ($(CUDA),1)
ifeq ($(UNAME_S),Darwin)
$(error CUDA=1 is supported only on Linux)
endif
ifneq ($(IS_WIN),)
# GPU: stub only in Phase 1 (G0). G1 builds coli_cuda.dll with MSVC+nvcc.
$(error CUDA=1 on Windows requires G1: build coli_cuda.dll with MSVC+nvcc (see PORT_WINDOWS_PLAN.md §8))
endif
CFLAGS   += -DCOLI_CUDA
LDFLAGS  += -L$(CUDA_HOME)/lib64 -Wl,-rpath,$(CUDA_HOME)/lib64 -lcudart -lstdc++
CUDA_OBJ  = backend_cuda.o
endif

# METAL=1 adds an opt-in Apple-GPU backend (macOS only). The shader is compiled at
# runtime, so no Xcode / offline metal compiler is required. Default build unchanged.
METAL     ?= 0
METAL_OBJ  =
METALXX    = clang++ -x objective-c++ -fobjc-arc -O3
ifeq ($(METAL),1)
ifneq ($(UNAME_S),Darwin)
$(error METAL=1 is supported only on macOS)
endif
CFLAGS   += -DCOLI_METAL
LDFLAGS  += -framework Metal -framework Foundation -lc++
METAL_OBJ = backend_metal.o
endif

all: glm$(EXE)

.PHONY: deepseek-v4
deepseek-v4:
	$(MAKE) -f Makefile.deepseek-v4 ARCH=$(ARCH) deepseek-v4

# phony 'glm' → 'glm.exe' on Windows (so 'make glm' and 'coli build' work on every platform)
glm: glm$(EXE)

glm$(EXE): glm.c st.h json.h tok.h tok_unicode.h compat.h grammar.h $(CUDA_OBJ) $(METAL_OBJ)
	$(CC) $(CFLAGS) glm.c $(CUDA_OBJ) $(METAL_OBJ) -o glm$(EXE) $(LDFLAGS)

backend_cuda.o: backend_cuda.cu backend_cuda.h
	@command -v $(NVCC) >/dev/null 2>&1 || { echo "nvcc not found: set CUDA_HOME or NVCC" >&2; exit 1; }
	$(NVCC) $(NVCCFLAGS) -c backend_cuda.cu -o $@

backend_metal.o: backend_metal.mm backend_metal.h
	$(METALXX) -c backend_metal.mm -o $@

metal-test: tests/test_backend_metal.mm backend_metal.mm backend_metal.h
	$(METALXX) tests/test_backend_metal.mm backend_metal.mm -framework Metal -framework Foundation -o backend_metal_test
	./backend_metal_test

cuda-test: backend_cuda.cu backend_cuda.h tests/test_backend_cuda.cu
	@command -v $(NVCC) >/dev/null 2>&1 || { echo "nvcc not found: set CUDA_HOME or NVCC" >&2; exit 1; }
	$(NVCC) $(NVCCFLAGS) backend_cuda.cu tests/test_backend_cuda.cu -o backend_cuda_test$(EXE)
	./backend_cuda_test$(EXE)

cuda-bench: backend_cuda.cu backend_cuda.h tests/bench_tensor_core.cu
	@command -v $(NVCC) >/dev/null 2>&1 || { echo "nvcc not found: set CUDA_HOME or NVCC" >&2; exit 1; }
	$(NVCC) $(NVCCFLAGS) backend_cuda.cu tests/bench_tensor_core.cu -o backend_cuda_bench$(EXE)
	./backend_cuda_bench$(EXE)

olmoe$(EXE): olmoe.c st.h json.h compat.h
	$(CC) $(CFLAGS) olmoe.c -o olmoe$(EXE) $(LDFLAGS)

# binario portabile da distribuire su altre macchine x86-64
portable:
	$(MAKE) glm$(EXE) ARCH=x86-64-v3

iobench$(EXE): iobench.c compat.h
	$(CC) $(CFLAGS) iobench.c -o iobench$(EXE) $(LDFLAGS)

tests/test_json$(EXE): tests/test_json.c json.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tests/test_st$(EXE): tests/test_st.c st.h json.h compat.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tests/test_tier$(EXE): tests/test_tier.c tier.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tests/test_grammar$(EXE): tests/test_grammar.c grammar.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tests/test_decode_batch$(EXE): tests/test_decode_batch.c decode_batch.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tests/test_idot$(EXE): tests/test_idot.c glm.c st.h json.h tok.h tok_unicode.h compat.h grammar.h tier.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tests/test_model_interfaces$(EXE): tests/test_model_interfaces.c model.h expert_store.h tensor.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tests/test_safetensors_index$(EXE): tests/test_safetensors_index.c safetensors_index.c safetensors_index.h json.h
	$(CC) $(CFLAGS) safetensors_index.c $< -o $@ $(LDFLAGS)

tests/test_native_quant$(EXE): tests/test_native_quant.c native_quant.c native_quant.h tensor.h
	$(CC) $(CFLAGS) native_quant.c $< -o $@ $(LDFLAGS)

tests/test_deepseek_v4_expert_store$(EXE): tests/test_deepseek_v4_expert_store.c deepseek_v4_expert_store.c deepseek_v4_expert_store.h safetensors_index.c safetensors_index.h expert_store.h tensor.h json.h
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_expert_store.c $< \
		-o $@ -pthread $(LDFLAGS)

tests/test_deepseek_v4_math$(EXE): tests/test_deepseek_v4_math.c deepseek_v4_math.c deepseek_v4_math.h
	$(CC) $(CFLAGS) deepseek_v4_math.c $< -o $@ $(LDFLAGS)

tests/test_deepseek_v4_expert$(EXE): tests/test_deepseek_v4_expert.c deepseek_v4_expert.c deepseek_v4_expert.h deepseek_v4_math.c deepseek_v4_math.h native_quant.c native_quant.h expert_store.h tensor.h
	$(CC) $(CFLAGS) native_quant.c deepseek_v4_math.c deepseek_v4_expert.c $< \
		-o $@ $(LDFLAGS)

tests/test_deepseek_v4_config$(EXE): tests/test_deepseek_v4_config.c deepseek_v4_config.c deepseek_v4_config.h json.h
	$(CC) $(CFLAGS) deepseek_v4_config.c $< -o $@ $(LDFLAGS)

tests/test_tensor_io$(EXE): tests/test_tensor_io.c tensor_io.c tensor_io.h native_quant.c native_quant.h safetensors_index.c safetensors_index.h tensor.h json.h
	$(CC) $(CFLAGS) safetensors_index.c native_quant.c tensor_io.c $< \
		-o $@ $(LDFLAGS)

tests/test_deepseek_v4_layer$(EXE): tests/test_deepseek_v4_layer.c deepseek_v4_layer.c deepseek_v4_layer.h deepseek_v4_config.h safetensors_index.c safetensors_index.h json.h
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_layer.c $< \
		-o $@ $(LDFLAGS)

tests/test_deepseek_v4_sparse_attention$(EXE): tests/test_deepseek_v4_sparse_attention.c deepseek_v4_sparse_attention.c deepseek_v4_sparse_attention.h native_quant.c native_quant.h
	$(CC) $(CFLAGS) deepseek_v4_sparse_attention.c native_quant.c $< -o $@ $(LDFLAGS)

tests/test_deepseek_v4_kv_cache$(EXE): tests/test_deepseek_v4_kv_cache.c deepseek_v4_kv_cache.c deepseek_v4_kv_cache.h
	$(CC) $(CFLAGS) deepseek_v4_kv_cache.c $< -o $@ $(LDFLAGS)

tests/test_deepseek_v4_attention_cache$(EXE): tests/test_deepseek_v4_attention_cache.c deepseek_v4_attention_cache.c deepseek_v4_attention_cache.h deepseek_v4_kv_cache.c deepseek_v4_kv_cache.h deepseek_v4_sparse_attention.c deepseek_v4_sparse_attention.h native_quant.c native_quant.h
	$(CC) $(CFLAGS) deepseek_v4_attention_cache.c deepseek_v4_kv_cache.c \
		deepseek_v4_sparse_attention.c native_quant.c $< -o $@ $(LDFLAGS)

tests/test_deepseek_v4_resource_plan$(EXE): tests/test_deepseek_v4_resource_plan.c deepseek_v4_resource_plan.c deepseek_v4_resource_plan.h
	$(CC) $(CFLAGS) deepseek_v4_resource_plan.c $< -o $@ $(LDFLAGS)

tests/test_deepseek_v4_prompt$(EXE): tests/test_deepseek_v4_prompt.c deepseek_v4_prompt.c deepseek_v4_prompt.h
	$(CC) $(CFLAGS) deepseek_v4_prompt.c $< -o $@ $(LDFLAGS)
probe-v4-layers: tools/probe_deepseek_v4_layers$(EXE)
	./tools/probe_deepseek_v4_layers$(EXE) $(MODEL) $(LAYER)

tools/probe_deepseek_v4_layers$(EXE): tools/probe_deepseek_v4_layers.c deepseek_v4_layer.c deepseek_v4_config.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c $< \
		-o $@ $(LDFLAGS)

probe-v4-attention: tools/probe_deepseek_v4_attention$(EXE)
	./tools/probe_deepseek_v4_attention$(EXE) $(MODEL) $(TOKEN) $(OUTPUT)

tools/probe_deepseek_v4_attention$(EXE): tools/probe_deepseek_v4_attention.c deepseek_v4_attention.c deepseek_v4_compressor.c deepseek_v4_indexer.c deepseek_v4_sparse_attention.c deepseek_v4_layer.c deepseek_v4_config.c deepseek_v4_math.c native_quant.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c \
		deepseek_v4_math.c native_quant.c deepseek_v4_sparse_attention.c \
		deepseek_v4_compressor.c deepseek_v4_indexer.c deepseek_v4_attention.c $< -o $@ $(LDFLAGS)

probe-v4-block: tools/probe_deepseek_v4_block$(EXE)
	./tools/probe_deepseek_v4_block$(EXE) $(MODEL) $(TOKEN) $(OUTPUT)

tools/probe_deepseek_v4_block$(EXE): tools/probe_deepseek_v4_block.c deepseek_v4_block.c deepseek_v4_attention.c deepseek_v4_compressor.c deepseek_v4_indexer.c deepseek_v4_sparse_attention.c deepseek_v4_expert.c deepseek_v4_expert_store.c deepseek_v4_layer.c deepseek_v4_config.c deepseek_v4_math.c native_quant.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c \
		deepseek_v4_math.c native_quant.c deepseek_v4_sparse_attention.c \
		deepseek_v4_compressor.c deepseek_v4_indexer.c deepseek_v4_attention.c \
		deepseek_v4_expert.c deepseek_v4_expert_store.c deepseek_v4_block.c $< \
		-o $@ -pthread $(LDFLAGS)

probe-v4-compressor: tools/probe_deepseek_v4_compressor$(EXE)
	./tools/probe_deepseek_v4_compressor$(EXE) $(MODEL) $(OUTPUT)

tools/probe_deepseek_v4_compressor$(EXE): tools/probe_deepseek_v4_compressor.c deepseek_v4_compressor.c deepseek_v4_layer.c deepseek_v4_config.c deepseek_v4_math.c native_quant.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c \
		deepseek_v4_math.c native_quant.c deepseek_v4_compressor.c $< -o $@ $(LDFLAGS)

probe-v4-ratio4-compressor: tools/probe_deepseek_v4_ratio4_compressor$(EXE)
	./tools/probe_deepseek_v4_ratio4_compressor$(EXE) $(MODEL) $(OUTPUT)

tools/probe_deepseek_v4_ratio4_compressor$(EXE): tools/probe_deepseek_v4_ratio4_compressor.c deepseek_v4_compressor.c deepseek_v4_layer.c deepseek_v4_config.c deepseek_v4_math.c native_quant.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c \
		deepseek_v4_math.c native_quant.c deepseek_v4_compressor.c $< -o $@ $(LDFLAGS)

probe-v4-indexer: tools/probe_deepseek_v4_indexer$(EXE)
	./tools/probe_deepseek_v4_indexer$(EXE) $(MODEL) $(OUTPUT)

tools/probe_deepseek_v4_indexer$(EXE): tools/probe_deepseek_v4_indexer.c deepseek_v4_indexer.c deepseek_v4_indexer.h deepseek_v4_compressor.c deepseek_v4_layer.c deepseek_v4_config.c deepseek_v4_math.c native_quant.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c \
		deepseek_v4_math.c native_quant.c deepseek_v4_compressor.c \
		deepseek_v4_indexer.c $< -o $@ $(LDFLAGS)

probe-v4-attention-sequence: tools/probe_deepseek_v4_attention_sequence$(EXE)
	./tools/probe_deepseek_v4_attention_sequence$(EXE) $(MODEL) $(OUTPUT)

tools/probe_deepseek_v4_attention_sequence$(EXE): tools/probe_deepseek_v4_attention_sequence.c deepseek_v4_attention.c deepseek_v4_compressor.c deepseek_v4_indexer.c deepseek_v4_sparse_attention.c deepseek_v4_layer.c deepseek_v4_config.c deepseek_v4_math.c native_quant.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c \
		deepseek_v4_math.c native_quant.c deepseek_v4_sparse_attention.c \
		deepseek_v4_compressor.c deepseek_v4_indexer.c deepseek_v4_attention.c $< -o $@ $(LDFLAGS)

deepseek-v4-first-token: tools/deepseek_v4_first_token$(EXE)
	./tools/deepseek_v4_first_token$(EXE) $(MODEL) $(TOKEN) $(COUNT)

deepseek-v4-tokenizer: tools/deepseek_v4_tokenizer$(EXE)
	./tools/deepseek_v4_tokenizer$(EXE) $(MODEL) "$(TEXT)"

tools/deepseek_v4_tokenizer$(EXE): tools/deepseek_v4_tokenizer.c tok.h tok_unicode.h json.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

tools/deepseek_v4_first_token$(EXE): tools/deepseek_v4_first_token.c tok.h tok_unicode.h json.h deepseek_v4_block.c deepseek_v4_attention.c deepseek_v4_sparse_attention.c deepseek_v4_compressor.c deepseek_v4_indexer.c deepseek_v4_expert.c deepseek_v4_expert_store.c deepseek_v4_layer.c deepseek_v4_config.c deepseek_v4_math.c native_quant.c tensor_io.c safetensors_index.c
	$(CC) $(CFLAGS) safetensors_index.c deepseek_v4_config.c deepseek_v4_layer.c \
		deepseek_v4_math.c native_quant.c tensor_io.c deepseek_v4_attention.c \
		deepseek_v4_compressor.c deepseek_v4_indexer.c \
		deepseek_v4_sparse_attention.c deepseek_v4_expert.c \
		deepseek_v4_expert_store.c deepseek_v4_block.c $< \
		-o $@ -pthread $(LDFLAGS)
test-c: $(TEST_BINS)
	@for test in $(TEST_BINS); do ./$$test || exit 1; done

test-python:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

test: test-c test-python

# Local validation: one portable CPU build and dependency-free tests.
check:
	$(MAKE) clean
	$(MAKE) portable
	$(MAKE) test

clean:
	rm -f olmoe$(EXE) glm$(EXE) iobench$(EXE) backend_cuda.o backend_cuda_test$(EXE) backend_cuda_bench$(EXE) backend_metal.o backend_metal_test $(TEST_BINS) $(V4_TOOL_BINS)
	rm -rf tests/__pycache__

.PHONY: all glm cuda-test cuda-bench portable test-c test-python test check clean \
	probe-v4-layers probe-v4-attention probe-v4-block probe-v4-compressor \
	probe-v4-ratio4-compressor probe-v4-indexer probe-v4-attention-sequence \
	deepseek-v4-first-token deepseek-v4-tokenizer
