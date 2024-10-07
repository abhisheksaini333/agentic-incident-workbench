export function mergeQueue(current, incoming) {
  const previous = new Map(current.map((item) => [item.id, item]));
  return incoming.map((item) => {
    const old = previous.get(item.id);
    return old && old.revision > item.revision ? old : item;
  });
}
export function mergeSnapshot(current, snapshot) {
  return current.map((item) =>
    item.id === snapshot.id && snapshot.revision > item.revision
      ? {
          ...item,
          status: snapshot.status,
          revision: snapshot.revision,
          title: snapshot.title,
          service: snapshot.service,
        }
      : item
  );
}
