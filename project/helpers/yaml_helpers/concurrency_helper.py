import helpers.cache_helpers.cacher as cacher
import logging.handlers
import logging
import aiohttp
import asyncio


def reorganize_results(results):
    """
    Reorganize results from multiprocess processing.
    """

    reorganized_results = {}
    total_num_entries = 0

    # result = (config, result_dict)
    for result in results:
        if not result:
            continue

        (config, result_dict, num_entries_parsed) = result
        slug = config["slug"]

        if not result_dict:
            logging.error(f"Error processing {slug}")
            continue

        if slug not in reorganized_results:
            reorganized_results[slug] = {
                "slug": slug,
                "aggregated_entries": [],
                "feed_data": result_dict["feed_data"],
                "feed_type": result_dict["feed_type"],
            }

        reorganized_results[slug]["aggregated_entries"].extend(
            result_dict["filtered_entries"]
        )

        total_num_entries += num_entries_parsed

    return reorganized_results.values(), total_num_entries


async def fetch_url(config, url, caching=False):
    """
    Fetch URL and return status code and data.
    """

    slug_url = config["slug"] + url
    cache_data = cacher.fetch_cache(slug_url) if caching else None
    last_seen_id, etag_value, last_modified_value = cache_data or (
        None,
        None,
        None,
    )

    headers = {}
    if etag_value:
        headers["ETAG"] = etag_value
    if last_modified_value:
        headers["If-Modified-Since"] = last_modified_value

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if caching:
                    etag_value = response.headers.get("Etag")
                    last_modified_value = response.headers.get("Last-Modified")
                    cacher.update_cache_etag_last(
                        slug_url, etag_value, last_modified_value
                    )

                if response.status == 304:
                    data = None
                    return (
                        response.status,
                        config,
                        url,
                        data,
                        caching,
                        cache_data,
                    )
                elif response.status == 404:
                    logging.error(
                        f"Error Fetching slug: {config['slug']}, URL: {url}"
                    )
                    logging.error("Error Resource not found. Received 404.")
                    return None
                data = await response.text()
                return (
                    response.status,
                    config,
                    url,
                    data,
                    caching,
                    cache_data,
                )

    except aiohttp.ClientError as e:
        logging.error(f"Error Fetching slug: {config['slug']}, URL: {url}")
        logging.error(f"Error {e}")
        return None


async def fetch_all_urls(yaml_config, caching=False):
    """
    Fetch all URLs with async.
    """
    slug_counts = {}
    tasks = []

    for config in yaml_config:
        slug = config["slug"]
        if slug not in slug_counts:
            slug_counts[slug] = {"total": 0, "304s": 0}

        for url in config["urls"]:
            slug_counts[slug]["total"] += 1
            tasks.append(fetch_url(config, url, caching))

    logging.info("")
    logging.info("Fetching all URLs")
    results = await asyncio.gather(*tasks)
    logging.info("Finished fetching all URLs")
    logging.info("")

    total_num_urls = len(tasks)
    filtered_results = []
    num_urls_fetched = 0
    num_urls_cached = 0

    for result in results:
        if result is not None:
            slug = result[1]["slug"]

            if result[0] == 304:
                slug_counts[slug]["304s"] += 1
                num_urls_cached += 1
            else:
                filtered_results.append(result)
                num_urls_fetched += 1

    all_304_slugs = [
        slug
        for slug, counts in slug_counts.items()
        if counts["total"] == counts["304s"]
    ]

    return (
        (total_num_urls, num_urls_fetched, num_urls_cached),
        filtered_results,
        all_304_slugs,
    )


def async_run(yaml_config, caching=False):
    """
    Run async fetch for all URLs.
    """

    return asyncio.run(fetch_all_urls(yaml_config, caching))
