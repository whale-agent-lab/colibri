.PHONY: all glm deepseek-v4 portable test check cuda-test clean

all glm deepseek-v4 portable test check cuda-test clean:
	$(MAKE) -C c $@
