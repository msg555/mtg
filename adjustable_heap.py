"""
Implements a heap with dynamically adjustable keys.
"""
from typing import Callable, Generic, List, Optional, TypeVar


TK = TypeVar("TK")
TV = TypeVar("TV")
KeyFunc = Callable[[TV], TK]


class AdjustableHeapKey(Generic[TK, TV]):
    """
    Object wrapper to store heap object metadata. Client code should treat
    this object as an opaque key that can be passed back to adjust_key() to
    change the value associated with an object.
    """

    def __init__(self, val: TV, comp_key: TK, index: int):
        self.val = val
        self.comp_key = comp_key
        self.index = index


class AdjustableHeap(Generic[TK, TV]):
    """
    Implements a dynamically adjustable heap.
    """

    def __init__(self, key_func: Optional[KeyFunc] = None) -> None:
        """
        Constructs an empty heap.
        """
        self.key_func = key_func
        self.heap: List[AdjustableHeapKey[TK, TV]] = []

    def push(self, val) -> AdjustableHeapKey[TK, TV]:
        """
        Pushes a new value to the heap.
        """
        comp_key = self.key_func(val) if self.key_func else val
        key = AdjustableHeapKey(val, comp_key, len(self.heap))
        self.heap.append(key)
        self._adjust(key)
        return key

    def pop(self) -> TV:
        """
        Removes the minimum element from the heap and returns it.
        """
        result = self.heap[0].val

        if len(self.heap) == 1:
            self.heap.clear()
        else:
            self.heap[0] = self.heap.pop()
            self.heap[0].index = 0
            self._adjust(self.heap[0])

        return result

    def peek(self) -> TV:
        """
        Returns the minimum element from the heap without removing it.
        """
        return self.heap[0].val

    def adjust_key(self, key: AdjustableHeapKey[TK, TV], val: TV) -> None:
        """
        Sets the value of an existing object using its heap key and adjusts
        its position within the heap.
        """
        key.val = val
        key.comp_key = self.key_func(val) if self.key_func else val
        self._adjust(key)

    def remove(self, key: AdjustableHeapKey[TK, TV]) -> None:
        """
        Remove an element from the heap given its heap key.
        """
        last_key = self.heap.pop()
        if last_key is key:
            return

        self.heap[key.index] = last_key
        last_key.index = key.index
        self._adjust(last_key)

    def _adjust(self, key: AdjustableHeapKey[TK, TV]) -> None:
        """
        Moves an object up and down within the heap depending on how its
        value has been changed.
        """
        # Bubble key up.
        index = key.index
        while index > 0:
            parent_index = (index + 1) // 2 - 1
            parent = self.heap[parent_index]

            if not key.comp_key < parent.comp_key:  # type: ignore
                break

            self.heap[index] = parent
            parent.index = index

            index = parent_index

        # Bubble key down.
        while 2 * index + 1 < len(self.heap):
            min_index = min(
                (ind for ind in (index * 2 + 1, index * 2 + 2) if ind < len(self.heap)),
                key=lambda ind: self.heap[ind].comp_key,
            )

            if key.comp_key < self.heap[min_index].comp_key:  # type: ignore
                break

            self.heap[index] = self.heap[min_index]
            self.heap[index].index = index
            index = min_index

        self.heap[index] = key
        key.index = index

    def __len__(self) -> int:
        """
        Returns the number of elements in the heap.
        """
        return len(self.heap)

    def __bool__(self) -> bool:
        """
        Returns true if the heap is empty.
        """
        return bool(self.heap)
