"""Release checks run off the GTK loop; installation owns a separate terminal."""
import shlex
import shutil

from gi.repository import Adw, Gio

from ... import __version__
from ...updater import check


def show_update(window):
    t = window.state.t
    dialog = Adw.MessageDialog(
        transient_for=window, modal=True,
        heading=t('update.title'),
        body=t('update.checking'))
    dialog.add_response('close', t('common.close'))
    dialog.set_close_response('close')
    alive = [True]

    def response(_dialog, name):
        alive[0] = False
        if name == 'install':
            launcher = shutil.which('wayvoice')
            try:
                if not launcher:
                    raise RuntimeError(t('update.launcher_missing'))
                app = Gio.AppInfo.create_from_commandline(
                    shlex.join([launcher, 'update', '--interactive']), 'WayVoice update',
                    Gio.AppInfoCreateFlags.NEEDS_TERMINAL)
                app.launch([], None)
            except Exception as exc:
                error = Adw.MessageDialog(transient_for=window, modal=True,
                        heading=t('update.title'), body=str(exc) + '\nwayvoice update --install')
                error.add_response('close', 'OK')
                error.present()

    def failed(exc):
        if alive[0]:
            dialog.set_body(str(exc))

    def done(result):
        if not alive[0]:
            return
        if result['available']:
            dialog.set_body(t('update.available', installed=__version__, available=result['version']))
            dialog.add_response('install', t('update.install'))
            dialog.set_response_appearance('install', Adw.ResponseAppearance.SUGGESTED)
        else:
            dialog.set_body(t('update.current', version=__version__))

    dialog.connect('response', response)
    dialog.present()
    window.tasks.run(check, done, failed)
