.PHONY: test

test:
	@echo -e "\033[7munit tests\033[m"
	@for test in test/unit/* ; \
	do \
		echo -n "$$test " ; \
		PYTHONPATH=. $$test &> /dev/null \
		&& echo OK || echo NOK ; \
	done
	@echo -e "\033[7mfunctional tests\033[m"
	@for test in test/func/* ; \
	do \
		echo -n "$$test " ; \
		PYTHONPATH=. $$test &> /dev/null \
		&& echo OK || echo NOK ; \
	done
