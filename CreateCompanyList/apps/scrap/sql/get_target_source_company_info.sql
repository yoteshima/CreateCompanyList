SELECT
	company
	, url
	, source
	, DATE_FORMAT(add_date, '%Y/%m/%d') AS add_date
FROM
	companys_info
WHERE
	source = '{source}'
ORDER BY
	add_date
	, company
;