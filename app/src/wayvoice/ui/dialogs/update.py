"""Release checks run off the GTK loop; installation owns a separate terminal."""
import shlex
import shutil

from gi.repository import Adw, Gio

from ... import __version__
from ...updater import check


def show_update(window):
    ru = window.state.ui_lang == 'ru'
    dialog = Adw.MessageDialog(
        transient_for=window, modal=True,
        heading='Обновление WayVoice' if ru else 'WayVoice update',
        body='Проверка GitHub Releases…' if ru else 'Checking GitHub Releases…')
    dialog.add_response('close', 'Закрыть' if ru else 'Close')
    dialog.set_close_response('close')
    alive = [True]

    def response(_dialog, name):
        alive[0] = False
        if name == 'install':
            launcher = shutil.which('wayvoice')
            try:
                if not launcher:
                    raise RuntimeError('wayvoice launcher unavailable')
                app = Gio.AppInfo.create_from_commandline(
                    shlex.join([launcher, 'update', '--interactive']), 'WayVoice update',
                    Gio.AppInfoCreateFlags.NEEDS_TERMINAL)
                app.launch([], None)
            except Exception as exc:
                error = Adw.MessageDialog(transient_for=window, modal=True,
                        heading='WayVoice update', body=str(exc) + '\nwayvoice update --install')
                error.add_response('close', 'OK')
                error.present()

    def failed(exc):
        if alive[0]:
            dialog.set_body(str(exc))

    def done(result):
        if not alive[0]:
            return
        if result['available']:
            dialog.set_body((f"Установлена {__version__}. Доступна {result['version']}.\n"
                             'Установка откроется в терминале и потребует подтверждения. '
                             'Завершите диктовку; службы будут перезапущены. '
                             'После обновления закройте и откройте настройки.' if ru else
                             f"Installed: {__version__}. Available: {result['version']}.\n"
                             'Installation opens in a terminal and asks for confirmation. '
                             'Finish dictation; services will restart. Reopen settings afterwards.'))
            dialog.add_response('install', 'Установить…' if ru else 'Install…')
            dialog.set_response_appearance('install', Adw.ResponseAppearance.SUGGESTED)
        else:
            dialog.set_body('Установлена актуальная версия: ' + __version__ if ru else
                            'Up to date: ' + __version__)

    dialog.connect('response', response)
    dialog.present()
    window.tasks.run(check, done, failed)
