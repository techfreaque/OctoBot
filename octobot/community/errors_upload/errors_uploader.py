#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import aiohttp

import octobot_commons.logging


class ErrorsUploader:
    """
    ErrorsUploader manages errors posts to the error url
    """

    def __init__(self, upload_url):
        self.upload_url = upload_url
        self.loop = None
        self.upload_delay = 1

        self._to_upload_errors = []
        self._upload_task = None

        self.logger = octobot_commons.logging.get_logger(self.__class__.__name__)

    def schedule_error_upload(self, error):
        """
        Called to schedule an error upload
        :param error: the octobot_commons.logging.error_model.Error to upload
        """
        self._to_upload_errors.append(error)
        self._ensure_upload_task()

    def _ensure_upload_task(self):
        if self._ensure_event_loop() and self._upload_task is None or self._upload_task.done():
            try:
                self._upload_task = self.loop.create_task(
                    self._upload_soon()
                )
            except Exception as err:
                self.logger.exception(
                    err,
                    True,
                    f"Error when uploading exception: {err}",
                    skip_post_callback=True,
                )

    async def _upload_error(self, session, error):
        async with session.post(self.upload_url, json={"_data": error.to_dict()}) as resp:
            if resp.status != 200:
                self.logger.debug(
                    f"Impossible to upload error : status code: {resp.status}, text: {await resp.text()}"
                )

    async def _upload_soon(self):
        try:
            await asyncio.sleep(self.upload_delay)

            async with aiohttp.ClientSession() as session:
                errors = self._to_upload_errors
                self._to_upload_errors = []
                await asyncio.gather(*(self._upload_error(session, e) for e in errors))
                self.logger.debug(f"Uploaded {len(errors)} errors")
        except Exception as err:
            self.logger.exception(
                err, True, f"Error when uploading exception: {err}", skip_post_callback=True
            )

    def _ensure_event_loop(self):
        if self.loop is not None:
            if self.loop.is_running():
                return True
            # otherwise, use the current loop
        try:
            self.loop = asyncio.get_event_loop()
            return True
        except RuntimeError:
            return False