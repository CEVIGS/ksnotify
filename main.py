import base64
from datetime import date, datetime
from kegscraper import bromcom as bc
import os
import discord
import asyncio
import aiohttp
import io
import colorgram
from PIL import Image

URL = os.environ["BSCRT_URL"]

def img_from_bytes(img_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(img_bytes))

def to_b64(img: Image.Image):
    # https://stackoverflow.com/questions/31826335/how-to-convert-pil-image-image-object-to-base64-string
    buffer = io.BytesIO()
    img.save(buffer, "JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def get_anomalies(table: list[bc.Lesson], mode: dict[str, dict[str, dict[str, bc.Lesson]]]) -> list[bc.Lesson]:
    ret = []
    for lesson in table:
        associated_lesson = mode[lesson.week_a_b][lesson.start.strftime("%A")][lesson.period]
        if any((
            lesson.room != associated_lesson.room,
            lesson.subject != associated_lesson.subject,
            lesson.teacher != associated_lesson.teacher
        )):
            ret.append(lesson)
    return ret


async def main():
    sess = bc.login(
        int(os.environ["BSCRT_ID"]),
        os.environ["BSCRT_UN"],
        os.environ["BSCRT_PW"]
    )
    # user_id = os.environ["BSCRPT_DID"]
    # mention = f"<@{user_id}>"

    assert sess.name
    username = sess.name.title()
    pfp_img = img_from_bytes(sess.pfp)
    pfp = to_b64(pfp_img)
    # return  
    async with aiohttp.ClientSession() as aiohttp_session:
        webhook = discord.Webhook.from_url(URL, session=aiohttp_session)
        async def set_pfp(name: str, avatar: str):
            return await aiohttp_session.patch(URL, json={
                "name": name,
                "avatar": avatar 
            })
        
        lessons = get_anomalies(sess.get_timetable_list(), sess.get_mode_timetables())

        week = "?"
        if lessons:
            week = lessons[0].week_a_b.upper()

        embed = discord.Embed(title=f"{date.today():%A} ({week})")
        r, g ,b = colorgram.extract(pfp_img, 1)[0].rgb
        embed.color = b + 256 * (g + 256 * r)
        embed.add_field(name="Timetable", value='\n'.join(f"{lesson.start:%a} {lesson.subject} @{lesson.room} ({lesson.teacher})" for lesson in lessons))
        embed.add_field(name="Attendance", value=f"{
            '\n'.join(
                f"{x.get("periods")}: {x.get("markDescription")}" 
                for x in sess.attendance_status.get("attendanceList", []
                ))}")

        await set_pfp(username, pfp)
        await webhook.send(embed=embed, username=username)
        

if __name__ == "__main__":
    asyncio.run(main())
