# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import re
import sys
import json
import datetime
import shutil
import subprocess
import time
import signal
import zipfile
from multiprocessing import Process, Queue
from functools import wraps
from threading import Timer
import platform
import common
from common import log, pjoin, rjoin

def run_windows(name, tl, ml, input = None, output = None):
	'''
	On windows, memory limit is not considered.
	'''
	t = time.clock()
	try:
		fin = (open(input) if input else None)
		fout = (open(output, 'w') if output else None)
		pro = subprocess.Popen(name, stdin = fin, stdout = fout)
		if fout:
			fout.close()
		if fin:
			fin.close()
	except:
		return 'Can\'t run program.', 0.0
	while True:
		ret = pro.poll()
		if ret != None:
			t = time.clock() - t
			if ret == 0:
				ret = None
			else:
				ret = 'Runtime error %d.' % ret
			break
		if (time.clock() - t) >= tl * common.time_multiplier:
			pro.kill()
			t = 0.0
			ret = 'Time out.'
			break
		time.sleep(1e-2)
	time.sleep(1e-2)
	return ret, t

def runner_linux(name, que, ml, input = None, output = None):
	pro = subprocess.Popen(
		'ulimit -v %d; time -f "%%U" -o timer ./%s %s %s' % (
			int(common.Memory(ml).KB),
			name,
			'< %s' % input if input else '',
			'> %s' % output if output else '',
		),
		shell = True,
		preexec_fn = os.setsid
	)
	que.put(pro.pid)
	ret = pro.wait()
	que.put(ret)
	
def run_linux(name, tl, ml, input = None, output = None):
	que = Queue()
	pro = Process(target = runner_linux, args = (name, que, ml, input, output))
	pro.start()
	pro.join(tl * common.time_multiplier)
	if que.qsize() == 0:
		fatal('Runner broken.')
	elif que.qsize() == 1:
		ret = 'Time out.'
		pid = que.get()
		os.killpg(os.getpgid(pid), signal.SIGTERM)
		t = 0.
	else:
		pid = que.get()
		ret = que.get()
		if ret == 0:
			try:
				t = float(open('timer').readline())
			except:
				log.warning('Timer broken.')
				t = 0.
			ret = None
		else:
			ret = 'Runtime error %d.' % ret
			t = 0.
	return ret, t

def runner_mac(name, que, ml, input = None, output = None):
	pro = subprocess.Popen(
		'ulimit -v %d; (time -p ./%s %s %s) 2> timer' % (
			int(common.Memory(ml).KB),
			name,
			'< %s' % input if input else '',
			'> %s' % output if output else '',
		),
		shell = True,
		preexec_fn = os.setsid
	)
	que.put(pro.pid)
	ret = pro.wait()
	que.put(ret)

def run_mac(name, tl, ml, input = None, output = None):
	que = Queue()
	pro = Process(target = runner_mac, args = (name, que, ml, input, output))
	pro.start()
	pro.join(tl * common.time_multiplier)
	if que.empty():
		common.fatal('Runner broken.')
	else:
		pid = que.get()
		if que.empty():
			ret = 'Time out.'
			os.killpg(os.getpgid(pid), signal.SIGTERM)
			t = 0.
		else:
			ret = que.get()
			if ret == 0:
				try:
					with open('timer') as f:
						f.readline()
						s = f.readline()
						t = float(s.split()[-1])
				except:
					common.warning('Timer broken.')
					t = 0.
				ret = None
			else:
				ret = 'Runtime error %d.' % ret
				t = 0.
	return ret, t

if common.system == 'Linux':
	run = run_linux
elif common.system == 'Windows':
	run = run_windows
elif common.system == 'Darwin':
	run = run_mac
	
def compile(prob):
	for lang, args in prob['compile'].items():
		if os.path.exists(pjoin('tmp', prob['name'] + '.' + lang)):
			os.chdir('tmp')
			ret = subprocess.call(
				common.compilers[lang](prob['name'], args, common.macros[common.work]),
				shell = True,
				stdout = open('log', 'w'),
				stderr = subprocess.STDOUT
			)
			os.chdir('..')
			return '`' + prob['name'] + '.' + lang + '` compile failed.' if ret != 0 else None
	else:
		return 'Can\'t find source file.'
	return None
	
def test(prob):
	scores = []
	times = []
	reports = []
	if prob['type'] == 'program':
		res = compile(prob)
		if res:
			for i in range(len(prob.test_cases) + len(prob.sample_cases)):
				scores.append(0.0)
				times.append(0.0)
				reports.append(res)
			return scores, times, reports
	all_cases = prob.test_cases + prob.sample_cases
	for case in all_cases:
		print('Case %s:%s  ' % (case['key'], case), end = '\r')
		sys.stdout.flush()
		shutil.copy(case.full() + '.in', pjoin('tmp', 'in'))
		shutil.copy(case.full() + '.ans', pjoin('tmp', 'ans'))
		for fname in ('in', 'ans'):
			if common.system == 'Windows':
				common.unix2dos(pjoin('tmp', fname))
			else:
				common.dos2unix(pjoin('tmp', fname))
		if prob['type'] == 'program':
			os.chdir('tmp')
			ret, time = run(prob['name'], prob['time limit'], prob['memory limit'], 'in', 'out')
			os.chdir('..')
		elif prob['type'] == 'output':
			if os.path.exists(pjoin('tmp', case['case'] + '.out')):
				shutil.copy(pjoin('tmp', case['case'] + '.out'), pjoin('tmp', 'out'))
				ret = None
				time = 0.0
			else:
				ret = 'Output file does not exist.'
				time = 0.0
		else:
			log.error(u'错误的题目类型`%s`。' % prob['type'])
			raise Exception('problem type error.')
		if not ret:
			if not os.path.exists(pjoin('tmp', 'out')):
				ret = 'Output file does not exist.'
				time = 0.0
				score = 0.0
			elif prob.chk:
				shutil.copy(pjoin('bin', prob.route), pjoin('tmp', 'chk' + common.elf_suffix))
				open('100.0', 'w').write('100.0\n')
				os.system('%s %s %s %s 100.0 tmp/score tmp/info' % (
					pjoin('tmp', 'chk' + common.elf_suffix),
					pjoin('tmp', 'in'),
					pjoin('tmp', 'out'),
					pjoin('tmp', 'ans')
				))
				os.remove('100.0')
				try:
					arbiter_out = ('/' if common.system != 'Windows' else '') + 'tmp/_eval.score'
					f = open(arbiter_out)
					report = f.readline().strip()
					score = float(f.readline()) * 0.1
					f.close()
					shutil.remove(arbiter_out)
				except Exception as e:
					try:
						report = open('tmp/info').read().strip()
					except Exception as e:
						report = ''
					score = float(open('tmp/score').readline()) * .01
			else:
				ret = os.system('%s %s %s > log' % (
					common.diff_tool,
					pjoin('tmp', 'ans'),
					pjoin('tmp', 'out')
				))
				if ret == 0:
					score = 1.0
					report = 'ok'
					if time > prob['time limit']:
						score = 0.0
						report += '(but time out)'
				else:
					score = 0.0
					report = 'wa'
					if time > prob['time limit']:
						report += '(and time out)'
		else:
			score = 0.0
			report = ret
		while os.path.exists(pjoin('tmp', prob['name'] + '.out')):
			try:
				os.remove(pjoin('tmp', prob['name'] + '.out'))
			except:
				pass
		scores.append(score)
		times.append(time)
		reports.append(report)
	return scores, times, reports

def packed_score(scores, times, reports, score_map, prob):
	pscore = []
	ptime = []
	preport = []
	for datum in prob.data:
		pscore.append(datum.score * min((scores[score_map[i]] for i in datum['cases'])))
		ptime.append(sum((times[score_map[i]] for i in datum['cases'] if scores[score_map[i]] > 0)))
		preport.append('Total %.1f' % datum.score)
	pscore.append(sum(pscore))
	ptime.append(sum(ptime))
	preport.append('')
	return (pscore, ptime, preport)
	
def test_problem(prob):
	log.info(u'尝试评测题目`%s`。' % prob.route)
	if 'users' not in prob:
		log.warning(u'题目`%s`缺少`users`字段，使用`python -m generator code`搜索源代码。' % prob.route)
		return
	if 'data' not in prob or len(prob.test_cases) == 0:
		log.warning(u'题目`%s`缺少`data`字段，使用`python -m generator data`在文件夹`%s`下搜索测试数据。' % (
			prob.route, pjoin(prob.path, 'data')
		))
	if 'samples' not in prob or len(prob.sample_cases) == 0:
		log.warning(u'题目`%s`缺少`samples`字段，使用`python -m generator samples`在文件夹`%s`下搜索样例数据。' % (
			prob.route, pjoin(prob.path, 'down')
		))
	log.info(u'共%d组样例，%d个测试点，%s打包评测%s。' % (
		len(prob.sample_cases),
		len(prob.test_cases),
		u'是' if prob['packed'] else u'不是',
		(u'（共%d个包）' % len(prob.data) if len(prob.data) != 1 else u'（看样子是一个包的ICPC赛制）') if prob['packed'] else ''
	))
	with open(pjoin('result', prob.route) + '.csv', 'w') as fres:
		fres.write('%s,%s%s,summary,sample%s\n' % (
			prob['name'],
			','.join(prob.test_cases),
			',' + ','.join(map(lambda datum : '{' + ';'.join(map(str, datum['cases'])) + '}', prob.data)) \
				if prob['packed'] else '',
			','.join(prob.sample_cases)
		))
		for user, algos in prob.users().items():
			if (not prob.all and not common.any_prefix(rjoin(prob.route, user))):
				continue
			for algo, path in algos.items():
				if (not prob.all and not common.any_prefix(rjoin(prob.route, user, algo))):
					continue
				if os.path.exists('tmp'):
					shutil.rmtree('tmp')
				if prob['type'] == 'program':
					os.makedirs('tmp')
					shutil.copy(path, pjoin('tmp', prob['name'] + '.' + path.split('.')[-1]))
				elif prob['type'] == 'output':
					shutil.copytree(path, 'tmp')
				log.info(u'测试程序 %s:%s:%s' % (prob['name'], user, algo))
				scores, times, reports = test(prob)
				while os.path.exists('tmp'):
					try:
						shutil.rmtree('tmp')
					except:
						pass
				tc = len(prob.test_cases)
				if 'packed' in prob and prob['packed']:
					score_map = {}
					for i in range(tc):
						score_map[prob.test_cases[i]] = i
					packed = packed_score(scores[:tc], times[:tc], reports[:tc], score_map, prob)
					scores = scores[:tc] + packed[0] + scores[tc:]
					times = times[:tc] + packed[1] + times[tc:]
					reports = reports[:tc] + packed[2] + reports[tc:]
				elif tc > 0:
					ratio = 100. / tc
					scores = [score * ratio for score in scores[:tc] + [sum(scores[:tc])] + scores[tc:]]
					times = times[:tc] + [sum((val for idx, val in enumerate(times[:tc]) if scores[idx] > 0))] + times[tc:]
					reports = reports[:tc] + [''] + reports[tc:]
				else:
					scores = [0.0, 0.0] + scores
					times = [0.0, 0.0] + times
					reports = ['', ''] + reports
				scores = map(lambda i : '%.1f' % i, scores)
				times = map(lambda i : '%.3f' % i, times)
				reports = map(lambda i : i.replace('\n', '\\n').replace(',', ';').replace('\r', ''), reports)
				for title, line in [(user, scores), (algo, times), ('', reports)]:
					fres.write('%s,%s\n' % (title, ','.join(line)))
	if common.start_file:
		common.xopen_file(pjoin('result', prob.route) + '.csv')

def test_progs():
	if common.conf.folder != 'problem' and not os.path.exists('result'):
		os.makedirs('result')
	for day in common.days():
		path = pjoin('result', day.route)
		if not os.path.exists(path):
			os.makedirs(path)
	for prob in common.probs():
		try:
			test_problem(prob)
		except Exception as e:
			log.error('At line %d: %s' % (e.__traceback__.tb_lineno, str(e)))

if __name__ == '__main__':
	try:
		if common.init():
			common.work = 'test'
			if common.do_pack:
				import packer
				common.run_exc(packer.test)
			common.run_exc(test_progs)
		else:
			log.info(u'这是测试出题人数据和程序的测试器，测试器没有细分的工作。')
	except common.NoFileException as e:
		log.error(e)
		log.info(u'尝试使用`python -m generator -h`获取如何生成一个工程。')
