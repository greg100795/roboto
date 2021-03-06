# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from feaTools import parser
from feaTools.writers.baseWriter import AbstractFeatureWriter


class KernFeatureWriter(AbstractFeatureWriter):
    """Generates a kerning feature based on glyph class definitions.

    Uses the kerning rules contained in an RFont's kerning attribute, as well as
    glyph classes from parsed OTF text. Class-based rules are set based on the
    existing rules for their key glyphs.
    """

    def __init__(self, font):
        self.kerning = font.kerning
        self.leftClasses = []
        self.rightClasses = []
        self.classSizes = {}

    def write(self, linesep="\n"):
        """Write kern feature."""

        # maintain collections of different rule types
        leftClassKerning, rightClassKerning, classPairKerning = {}, {}, {}
        for leftName, leftContents in self.leftClasses:
            leftKey = leftContents[0]

            # collect rules with two classes
            for rightName, rightContents in self.rightClasses:
                rightKey = rightContents[0]
                pair = leftKey, rightKey
                kerningVal = self.kerning[pair]
                if kerningVal is None:
                    continue
                classPairKerning[leftName, rightName] = kerningVal
                self.kerning.remove(pair)

            # collect rules with left class and right glyph
            for pair, kerningVal in self.kerning.getLeft(leftKey):
                leftClassKerning[leftName, pair[1]] = kerningVal
                self.kerning.remove(pair)

        # collect rules with left glyph and right class
        for rightName, rightContents in self.rightClasses:
            rightKey = rightContents[0]
            for pair, kerningVal in self.kerning.getRight(rightKey):
                rightClassKerning[pair[0], rightName] = kerningVal
                self.kerning.remove(pair)

        # write the feature
        self.ruleCount = 0
        lines = ["feature kern {"]
        lines.append(self._writeKerning(self.kerning, linesep))
        lines.append(self._writeKerning(leftClassKerning, linesep, True))
        lines.append(self._writeKerning(rightClassKerning, linesep, True))
        lines.append(self._writeKerning(classPairKerning, linesep))
        lines.append("} kern;")
        return linesep.join(lines)

    def _writeKerning(self, kerning, linesep, enum=False):
        """Write kerning rules for a mapping of pairs to values."""

        lines = []
        enum = "enum " if enum else ""
        pairs = kerning.items()
        pairs.sort()
        for (left, right), val in pairs:
            if enum:
                rulesAdded = (self.classSizes.get(left, 1) *
                              self.classSizes.get(right, 1))
            else:
                rulesAdded = 1
            self.ruleCount += rulesAdded
            if self.ruleCount > 2048:
                lines.append("    subtable;")
                self.ruleCount = rulesAdded
            lines.append("    %spos %s %s %d;" % (enum, left, right, val))
        return linesep.join(lines)

    def classDefinition(self, name, contents):
        """Store a class definition as either a left- or right-hand class."""

        if not name.startswith("@_"):
            return
        info = (name, contents)
        if name.endswith("_L"):
            self.leftClasses.append(info)
        elif name.endswith("_R"):
            self.rightClasses.append(info)
        self.classSizes[name] = len(contents)


def makeKernFeature(font, text):
    """Add a kern feature to the font, using a KernFeatureWriter."""

    writer = KernFeatureWriter(font)
    parser.parseFeatures(writer, text)
    font.features.text += writer.write()
