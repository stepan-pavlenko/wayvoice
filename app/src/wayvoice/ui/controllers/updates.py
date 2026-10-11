"""Opt-in release checks; installation stays in the existing update dialog."""
import time

from ...updater import check


class UpdatesController:
    INTERVAL = 6 * 60 * 60
    RETRY = 60 * 60

    def __init__(self, context):
        self.ctx = context
        self.enabled = False
        self.pending = False
        self.generation = 0
        self.next_check = 0.0

    def configure(self, cfg):
        enabled = cfg.get('auto_check_updates') is True
        if enabled != self.enabled:
            self.enabled = enabled
            self.generation += 1
            self.next_check = 0.0
            if not enabled:
                self.ctx.home.update_banner.set_revealed(False)
                self.ctx.home.update_banner.set_visible(False)
        self.tick()

    def tick(self):
        if (not self.ctx.tasks.closed and self.enabled and not self.pending
                and not getattr(self.ctx.window, '_update_busy', False)
                and time.monotonic() >= self.next_check):
            generation = self.generation
            self.pending = True
            self.next_check = time.monotonic() + self.INTERVAL
            self.ctx.tasks.run(check,
                               lambda result: self._finished(generation, result),
                               lambda _exc: self._finished(generation, None))
        return True

    def _finished(self, generation, result):
        self.pending = False
        if self.ctx.tasks.closed:
            return
        if generation != self.generation:
            self.tick()
            return
        if result is None:
            self.next_check = time.monotonic() + self.RETRY
        else:
            self._paint(result)

    def checked(self, result):
        """Manual checks also keep Home's release notice current."""
        self.generation += 1
        self.next_check = time.monotonic() + self.INTERVAL
        self._paint(result)

    def _paint(self, result):
        banner = self.ctx.home.update_banner
        if result.get('available'):
            banner.set_title(self.ctx.state.t('update.notice', version=result['version']))
            banner.set_visible(True)
            banner.set_revealed(True)
        else:
            banner.set_revealed(False)
            banner.set_visible(False)
