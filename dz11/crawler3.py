#!/usr/bin/python3.6
# -*- coding: utf-8 -*-
import asyncio
import aiohttp




DICT_URLS_HTML={'1.html':'https://en.wikipedia.org/wiki/Tit_for_tat',
'2.html':'https://plato.stanford.edu/entries/prisoner-dilemma/',
'3.html':'https://en.wikipedia.org/wiki/Forbin_Project',
'4.html':'https://en.wikipedia.org/wiki/Colossus:_The_Forbin_Project'}

DICT_URLS_PDF={'1.pdf':""'https://en.wikipedia.org/wiki/Tit_for_tat'"",
'2.pdf':"'https://plato.stanford.edu/entries/prisoner-dilemma/'",
'3.pdf':"'https://en.wikipedia.org/wiki/Forbin_Project'",
'4.pdf':"'https://en.wikipedia.org/wiki/Colossus:_The_Forbin_Project'"}

async def get_body(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                    return await response.read()
    except aiohttp.ClientError as ex:
        print("aiohttp can't read response: %s" % ex)


def write_to_file( path, content):
    """
    Save binary content to file
    """
    try:
        with open(path, "wb") as f:
            f.write(content)
    except OSError as ex:
        print("Can't save file {}. {}: {}".format(path, type(ex).__name__, ex.args))
        return



'''async def pdf_converter(url,filehtml):
    """Run command in subprocess (shell)"""
    filepdf = filehtml.replace('html','pdf')
    content = await get_body(url)
    write_to_file(filehtml, content)
    wkhtmltopdf = '/usr/bin/xvfb-run -a -s "-screen 0 1024x768x16" /usr/bin/wkhtmltopdf'
    command = "{} {}, {}".format(wkhtmltopdf,filehtml,filepdf)
    # Create subprocess
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE)
    print('Started:', command, '(pid = ' + str(process.pid) + ')')

    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        print('Done:', command, '(pid = ' + str(process.pid) + ')')
    else:
        print('Failed:', command, '(pid = ' + str(process.pid) + ')')
    result = stdout.decode().strip()
    return result'''



async def pdf_converter(url,filepdf):
    """Run command in subprocess (shell)"""
    #filepdf = filehtml.replace('html','pdf')
    #content = await get_body(url)
    #write_to_file(filehtml, content)
    wkhtmltopdf = 'wkhtmltopdf   --load-error-handling ignore'
    command = "{} {} {}".format(wkhtmltopdf,url,filepdf)
    # Create subprocess
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE)
    print('Started:', command, '(pid = ' + str(process.pid) + ')')

    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        print('Done:', command, '(pid = ' + str(process.pid) + ')')
    else:
        print('Failed:', command, '(pid = ' + str(process.pid) + ')')
    result = stdout.decode().strip()
    return result






def main():
    loop = asyncio.get_event_loop()
    #workers = [run_command_shell(url, file_to_save)]
    '''workers = [
        pdf_converter(url, fname)
        for fname,url in DICT_URLS_HTML.items()
    ]'''
    workers = [
        pdf_converter(url, fname)
        for fname,url in DICT_URLS_PDF.items()
    ]
    results =loop.run_until_complete(asyncio.gather(*workers))
    print(results)
    loop.close()

if __name__ == '__main__':
   main()
