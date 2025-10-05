
media: portal2-ost.zip
	mkdir -p media
	unzip -o $< -d media

.PHONY: test
test:
	pytest -v test

portal2-ost.zip:
	wget http://media.steampowered.com/apps/portal2/soundtrack/Portal2-OST-Complete.zip -O $@

run-render:
	./media_render.py render.config

run-server:
	./media_server.py server.config

clean:
	$(RM) -r spotifice*.py __pycache__ *.zip
